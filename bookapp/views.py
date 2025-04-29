from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login

from django.views import View

from django.contrib.auth.models import User
from django.contrib.auth import logout
from django.utils.decorators import method_decorator
from django.db.models import Q

# Create your views here.

from django.contrib.auth import authenticate, login
from django.http import HttpResponse

from bookapp.forms import UserRegistrationForm
from bookapp import models


def index(request):
    return HttpResponse("Hello, world. You're at the polls index.")


def check_if_admin_or_user(view_func):
    def wrapper(request, *args, **kwargs):
        user_type = "staff_user" if request.user.is_staff else "user"
        if not request.user.is_staff and request.path in [
            "/admin-book-list/",
            "/admin-book-detail/",
            "/admin-book-request-list/",
        ]:
            logout(request)
            return redirect("login_page")

        elif request.user.is_staff and request.path not in [
            "/admin-book-list/",
            "/admin-book-detail/",
            "/admin-book-request-list/",
        ]:
            logout(request)
            return redirect("login_page")

        else:
            request.access = True
        return view_func(request, *args, **kwargs)

    return wrapper


class LogoutView(View):
    def get(self, request, *args, **kwargs):
        logout(request)
        return redirect("login_page")


class LoginView(View):
    def get(self, request, *args, **kwargs):
        return render(request, template_name="login.html")

    def post(self, request, *args, **kwargs):
        user_obj = authenticate(
            request,
            username=request.POST.get("email-username"),
            password=request.POST.get("password"),
        )

        if not user_obj:
            return render(
                request,
                template_name="login.html",
                context={"error": "Invalid Credentials"},
            )

        if user_obj and user_obj.is_staff and user_obj.is_active:
            login(request, user_obj)
            return redirect("admin_book_list")
        elif user_obj and user_obj.is_active:
            login(request, user_obj)
            return redirect("user_book_list")
        return redirect("login_page")


class RegisterView(View):
    def get(self, request, *args, **kwargs):
        form = UserRegistrationForm()
        return render(request, "register.html", {"form": form})

    def post(self, request, *args, **kwargs):
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data["password"])
            user.save()
            return redirect("login_page")
        return render(request, "register.html", {"form": form})


class IndexView(View):
    def get(self, request, *args, **kwargs):
        user_obj = User.objects.get(id=request.user.id)
        return render(request, template_name="index.html")


@method_decorator(check_if_admin_or_user, name="dispatch")
class AdminBookListView(View):
    def get(self, request, *args, **kwargs):
        """displays list of available books for admin"""
        if request.GET.get("query"):
            book_obj = models.BookModel.objects.filter(
                book_title__icontains=request.GET.get("query")
            ).values()
        else:
            book_obj = models.BookModel.objects.values()

        for obj in book_obj:
            if models.BookAllotmentModel.objects.filter(
                book=obj.get("id"), status="approved"
            ).exists():
                obj["available"] = False
            else:
                obj["available"] = True

            obj["book_img"] = obj.get("book_img").split("/")[1]

        return render(
            request,
            template_name="admin_book_list.html",
            context={"book_list": book_obj},
        )

    def post(self, request, *args, **kwargs):
        if request.POST.get("deletesubmit") and request.POST.get("book_id"):
            models.BookModel.objects.filter(id=request.POST.get("book_id")).delete()

        if request.POST.get("releasesubmit") and request.POST.get("book_id"):
            models.BookAllotmentModel.objects.filter(
                book__id=request.POST.get("book_id")
            ).delete()
        return redirect("admin_book_list")


class AdminBookStatusList(View):
    def get(self, request, *args, **kwargs):
        """displays books current status"""
        allot_obj = models.BookAllotmentModel.objects.values(
            "user__username", "book__book_title", "modefield_at", "status"
        )
        return render(
            request,
            template_name="admin_book_status.html",
            context={"book_list": allot_obj},
        )


@method_decorator(check_if_admin_or_user, name="dispatch")
class UserBookListView(View):
    """displays list of available books for users"""
    def get(self, request, *args, **kwargs):
        if request.GET.get("query"):
            book_obj = models.BookModel.objects.filter(
                book_title__icontains=request.GET.get("query")
            ).values()
        else:
            book_obj = models.BookModel.objects.values()
        for obj in book_obj:
            allot_obj = models.BookAllotmentModel.objects.filter(
                book=obj.get("id"), user=request.user
            ).first()
            if allot_obj:
                obj["available"] = allot_obj.status
            else:
                obj["available"] = None

            obj["occupied"] = (
                True if allot_obj and allot_obj.user != request.user else False
            )

            obj["book_img"] = obj.get("book_img").split("/")[1]
        return render(
            request,
            template_name="user_book_list.html",
            context={"book_list": book_obj},
        )

    def post(self, request, *args, **kwargs):
        models.BookAllotmentModel.objects.filter(user=request.user).delete()
        if request.POST.get("request_book"):
            book_obj = models.BookModel.objects.get(id=request.POST.get("request_book"))
            models.BookAllotmentModel.objects.create(
                user=request.user, book=book_obj, status="pending"
            )
            return redirect("user_book_list")


@method_decorator(check_if_admin_or_user, name="dispatch")
class UserHistoryList(View):
    def get(self, request, *args, **kwargs):
        """displays users current activity"""
        allot_obj = models.BookAllotmentModel.objects.filter(user=request.user).values(
            "user__username", "book__book_title", "modefield_at", "status"
        )
        return render(
            request,
            template_name="user_book_status.html",
            context={"book_list": allot_obj},
        )


@method_decorator(check_if_admin_or_user, name="dispatch")
class AdminBookDetailView(View):
    def get(self, request, *args, **kwargs):
        """a form for admin to update or create a book"""
        book_obj = None
        if request.GET.get("book"):
            book_obj = (
                models.BookModel.objects.filter(id=request.GET.get("book"))
                .values()
                .first()
            )
            book_obj["book_img"] = book_obj.get("book_img").split("/")[1]

        return render(
            request,
            template_name="admin_book_detail.html",
            context={"book_obj": book_obj},
        )

    def post(self, request, *args, **kwargs):
        if request.GET.get("book"):
            book_obj = models.BookModel.objects.get(id=request.GET.get("book"))
            book_obj.book_title = request.POST.get("title")
            book_obj.activity_desc = request.POST.get("desc")
            if request.FILES.get("fileinput"):
                book_obj.book_img = request.FILES.get("fileinput")
            book_obj.save()
            return redirect("admin_book_list")
        models.BookModel.objects.create(
            book_title=request.POST.get("title"),
            activity_desc=request.POST.get("desc"),
            book_img=request.FILES.get("fileinput"),
        )
        return redirect("admin_book_list")


@method_decorator(check_if_admin_or_user, name="dispatch")
class AdminBookRequestListView(View):
    def get(self, request, *args, **kwargs):
        """admin can view all available requests"""
        user_obj = User.objects.get(id=request.user.id)
        book_list = models.BookAllotmentModel.objects.filter(status="pending").values(
            "id", "created_at", "modefield_at", "user__username", "book__book_title"
        )
        return render(
            request,
            template_name="admin_book_request.html",
            context={"book_lst": book_list},
        )

    def post(self, request, *args, **kwargs):
        reject_lst = []
        approve_lst = []
        if request.POST:
            for ele in request.POST:
                if "reject" in ele:
                    reject_lst.append(request.POST.get(ele))
                elif "approved" in ele:
                    approve_lst.append(request.POST.get(ele))
        models.BookAllotmentModel.objects.filter(id__in=reject_lst).update(
            status="rejected"
        )
        models.BookAllotmentModel.objects.filter(id__in=approve_lst).update(
            status="approved"
        )
        return redirect("admin_book_request_list")

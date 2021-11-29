from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required


def index(request):
    return render(
        request,
        "pages/dashboard.html",
        {}
    )


def sign_in(request):
    if request.user.is_authenticated:
        return redirect("index")
    if request.method == "POST":
        user = authenticate(
            email=request.POST.get("email"),
            password=request.POST.get("password")
        )
        if user is not None:
            login(request, user)
            return redirect("index")
    return render(
        request,
        "pages/sign_in.html",
        {}
    )


def sign_out(request):
    if request.user.is_authenticated:
        logout(request)
    return redirect("index")
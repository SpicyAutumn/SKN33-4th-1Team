from django.contrib.auth.decorators import login_required
from django.shortcuts import render


def home(request):
    return render(request, "heritage/home.html")


@login_required
def mypage(request):
    return render(request, "heritage/mypage.html")

from django.urls import path

from . import views

app_name = "heritage"

urlpatterns = [
    path("", views.home, name="home"),
    path("mypage/", views.mypage, name="mypage"),
]

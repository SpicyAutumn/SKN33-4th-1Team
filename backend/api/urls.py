from django.urls import path

from . import views


urlpatterns = [
    path("health", views.health),
    path("auth/signup", views.signup),
    path("auth/login", views.login_view),
    path("auth/logout", views.logout_view),
    path("auth/me", views.me),
    path("history", views.search_history),
    path("chat", views.chat),
]

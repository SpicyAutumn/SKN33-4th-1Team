from django.urls import path

from . import views
from .network_views import heritage_network


urlpatterns = [
    path("v1/heritage-network", heritage_network),
    path("health", views.health),
    path("v1/auth/csrf", views.csrf),
    path("v1/auth/signup", views.signup),
    path("v1/auth/login", views.login_view),
    path("v1/auth/logout", views.logout_view),
    path("v1/auth/me", views.me),
    path("v1/searches", views.searches),
    path("v1/me/searches", views.my_searches),
    path("v1/me/searches/<uuid:record_id>", views.my_search_detail),
    path("v1/me/error-reports", views.error_reports),
    path("v1/me/error-reports/<uuid:report_id>", views.my_error_report_detail),
    path("v1/admin/error-reports", views.admin_error_reports),
    path("v1/admin/error-reports/<uuid:report_id>", views.admin_error_report_detail),
]

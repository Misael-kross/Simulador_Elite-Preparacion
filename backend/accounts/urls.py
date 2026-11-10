from django.contrib.auth.views import LogoutView
from django.urls import path

from .views import (
    EliteLoginView,
    bachillerato,
    dashboard,
    universidad,
)


urlpatterns = [
    path(
        "login/",
        EliteLoginView.as_view(),
        name="login",
    ),

    path(
        "logout/",
        LogoutView.as_view(),
        name="logout",
    ),

    path(
        "",
        dashboard,
        name="dashboard",
    ),

    path(
        "bachillerato/",
        bachillerato,
        name="bachillerato",
    ),

    path(
        "universidad/",
        universidad,
        name="universidad",
    ),
]
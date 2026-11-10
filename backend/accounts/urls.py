from django.contrib.auth.views import LogoutView
from django.urls import path

from .views import (
    EliteLoginView,
    dashboard,
    protected_content,
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
        "contenido/",
        protected_content,
        name="protected_content",
    ),
]
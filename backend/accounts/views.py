from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import render

from access_control.services import (
    get_valid_access_grants,
    user_has_product,
)


class EliteLoginView(LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True


@login_required
def dashboard(request):
    access_grants = get_valid_access_grants(
        request.user
    )

    return render(
        request,
        "accounts/dashboard.html",
        {
            "access_grants": access_grants,
        },
    )


@login_required
def bachillerato(request):
    if not user_has_product(
        request.user,
        "BACHILLERATO",
    ):
        return render(
            request,
            "accounts/access_denied.html",
            status=403,
        )

    return render(
        request,
        "accounts/bachillerato.html",
    )


@login_required
def universidad(request):
    if not user_has_product(
        request.user,
        "UNIVERSIDAD",
    ):
        return render(
            request,
            "accounts/access_denied.html",
            status=403,
        )

    return render(
        request,
        "accounts/universidad.html",
    )
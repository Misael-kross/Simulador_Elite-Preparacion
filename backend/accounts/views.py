from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.db.models import Q
from django.shortcuts import render
from django.utils import timezone

from access_control.models import AccessGrant


class EliteLoginView(LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True


def get_current_access_grants(user):
    now = timezone.now()

    return AccessGrant.objects.filter(
        user=user,
        is_active=True,
        starts_at__lte=now,
    ).filter(
        Q(expires_at__isnull=True)
        | Q(expires_at__gt=now)
    ).select_related("product")


@login_required
def dashboard(request):
    access_grants = get_current_access_grants(
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
def protected_content(request):
    access_grants = get_current_access_grants(
        request.user
    )

    if not access_grants.exists():
        return render(
            request,
            "accounts/access_denied.html",
            status=403,
        )

    return render(
        request,
        "accounts/protected_content.html",
        {
            "access_grants": access_grants,
        },
    )
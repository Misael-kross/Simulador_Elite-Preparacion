from django.db.models import Q
from django.utils import timezone

from .models import AccessGrant


def get_valid_access_grants(user):
    now = timezone.now()

    return AccessGrant.objects.filter(
        user=user,
        is_active=True,
        starts_at__lte=now,
    ).filter(
        Q(expires_at__isnull=True)
        | Q(expires_at__gt=now)
    ).select_related("product")


def user_has_product(user, product_code):
    return get_valid_access_grants(user).filter(
        product__code=product_code,
        product__is_active=True,
    ).exists()
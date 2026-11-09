from django.conf import settings
from django.db import models
from django.utils import timezone


class Product(models.Model):
    code = models.CharField(
        max_length=50,
        unique=True,
    )

    name = models.CharField(
        max_length=100,
    )

    description = models.TextField(
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return self.name


class AccessGrant(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="access_grants",
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="access_grants",
    )

    starts_at = models.DateTimeField()

    expires_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    notes = models.TextField(
        blank=True,
    )

    def __str__(self):
        return f"{self.user.username} - {self.product.name}"

    @property
    def is_valid(self):
        now = timezone.now()

        if not self.is_active:
            return False

        if self.starts_at > now:
            return False

        if self.expires_at and self.expires_at <= now:
            return False

        return True
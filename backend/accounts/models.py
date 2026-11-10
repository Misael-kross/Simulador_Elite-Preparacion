from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.username


class ActiveSession(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="active_session",
    )

    session_key = models.CharField(
        max_length=40,
        unique=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return f"Sesión activa de {self.user.username}"

    def terminate(self):
        from django.contrib.sessions.models import Session

        Session.objects.filter(
            session_key=self.session_key
        ).delete()

        self.delete()
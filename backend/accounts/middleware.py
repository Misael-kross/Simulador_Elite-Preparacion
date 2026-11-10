from django.contrib.sessions.models import Session

from .models import ActiveSession


class SingleActiveSessionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        was_authenticated = bool(
            user and user.is_authenticated
        )

        user_id = user.pk if was_authenticated else None
        session_key = (
            request.session.session_key
            if was_authenticated
            else None
        )

        if was_authenticated and session_key:
            active_session, created = ActiveSession.objects.get_or_create(
                user_id=user_id,
                defaults={
                    "session_key": session_key,
                },
            )

            if (
                not created
                and active_session.session_key != session_key
            ):
                Session.objects.filter(
                    session_key=active_session.session_key
                ).delete()

                active_session.session_key = session_key

                active_session.save(
                    update_fields=[
                        "session_key",
                        "updated_at",
                    ]
                )

        response = self.get_response(request)

        # Si durante esta petición se cerró sesión,
        # eliminamos también nuestro registro de control.
        current_user = getattr(request, "user", None)

        if (
            was_authenticated
            and current_user
            and not current_user.is_authenticated
        ):
            ActiveSession.objects.filter(
                user_id=user_id,
                session_key=session_key,
            ).delete()

        return response
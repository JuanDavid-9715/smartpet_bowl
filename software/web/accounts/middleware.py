"""El perfil local existe solo en la Raspberry y solo para la app.

La web publica nunca autentica a nadie: ahi se entra con correo y contrasena.
"""
from django.conf import settings
from django.contrib.auth import get_user_model

_cached_user = None
LOCAL_PREFIXES = ("/app/",)


def get_local_owner():
    global _cached_user
    if _cached_user is not None:
        return _cached_user
    User = get_user_model()
    _cached_user = User.objects.filter(profile__is_local_owner=True).first()
    return _cached_user


class LocalAutoLoginMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            settings.IS_LOCAL
            and not request.user.is_authenticated
            and request.path.startswith(LOCAL_PREFIXES)
        ):
            owner = get_local_owner()
            if owner is not None:
                request.user = owner
        return self.get_response(request)

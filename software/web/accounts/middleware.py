"""En modo local no se pide correo ni contrasena: se entra con el perfil de la casa."""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

_cached_user = None


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
        if settings.IS_LOCAL and not request.user.is_authenticated:
            owner = get_local_owner()
            if owner is not None:
                request.user = owner
            elif request.user is None:
                request.user = AnonymousUser()
        return self.get_response(request)

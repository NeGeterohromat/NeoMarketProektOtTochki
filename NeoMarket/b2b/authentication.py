# authentication.py
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework import exceptions

class ServiceKeyAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_key = request.META.get('HTTP_X_SERVICE_KEY')
        if not auth_key:
            return None

        valid_key = settings.MODERATION_TOKEN
        if auth_key != valid_key:
            raise exceptions.AuthenticationFailed('Invalid Service Key')

        # Возвращаем кастомный флаг в кортеже Auth, чтобы отличать модератора
        # Вместо None передаем словарь или объект, указывающий на сервис
        return (request.user, {'is_moderator_service': True})

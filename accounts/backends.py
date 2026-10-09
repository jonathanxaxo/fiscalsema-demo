from django.contrib.auth.backends import ModelBackend

from .models import AccountStatus


class AccountStatusBackend(ModelBackend):
    def user_can_authenticate(self, user):
        return user.is_active and user.status == AccountStatus.ACTIVE

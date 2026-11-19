from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.password_validation import validate_password


class UserManager(BaseUserManager):
    use_in_migrations = True

    @staticmethod
    def normalize_login_email(email):
        return BaseUserManager.normalize_email(email).strip().casefold()

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("O e-mail é obrigatório.")
        email = self.normalize_login_email(email)
        user = self.model(email=email, **extra_fields)
        validate_password(password, user=user)
        user.set_password(password)
        user.full_clean(exclude={"password"})
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        from .models import AccountStatus, UserProfile

        extra_fields.setdefault("profile", UserProfile.FISCAL_TITULAR)
        extra_fields.setdefault("status", AccountStatus.PENDING_APPROVAL)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        from .models import AccountStatus, UserProfile

        extra_fields.setdefault("profile", UserProfile.ADMINISTRATOR_GENERAL)
        extra_fields.setdefault("status", AccountStatus.ACTIVE)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("must_change_password", False)
        if extra_fields.get("profile") != UserProfile.ADMINISTRATOR_GENERAL:
            raise ValueError("Superusuário deve possuir perfil Administrador Geral.")
        if extra_fields.get("status") != AccountStatus.ACTIVE:
            raise ValueError("Superusuário deve estar ativo.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superusuário deve possuir is_superuser=True.")
        return self._create_user(email, password, **extra_fields)

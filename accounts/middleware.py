from django.shortcuts import redirect
from django.urls import resolve


class RequirePasswordChangeMiddleware:
    exempt_names = {
        "accounts:login",
        "accounts:logout",
        "accounts:password_change",
        "accounts:password_change_done",
        "accounts:password_reset",
        "accounts:password_reset_done",
        "accounts:password_reset_confirm",
        "accounts:password_reset_complete",
        "accounts:register",
        "accounts:registration_submitted",
        "health",
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and request.user.must_change_password:
            match = resolve(request.path_info)
            if match.view_name not in self.exempt_names:
                return redirect("accounts:password_change")
        return self.get_response(request)

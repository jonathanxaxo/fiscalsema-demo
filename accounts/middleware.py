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


class IdleSessionTimeoutMiddleware:
    """Sprint 49: encerra a sessão de qualquer perfil depois de um tempo sem uso (padrão: 1 hora).

    Cada requisição de uma pessoa logada atualiza a hora da última atividade. Se o intervalo
    passar do limite, a sessão é encerrada, o fato vai para a auditoria (LOGOUT, motivo
    inatividade) e a pessoa volta para a tela de entrada para digitar a senha de novo.
    """

    SESSION_KEY = "fiscalsema_ultima_atividade"
    exempt_names = {"accounts:login", "accounts:logout", "health"}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from django.conf import settings

        timeout = int(getattr(settings, "SESSION_IDLE_TIMEOUT_SECONDS", 3600) or 0)
        if timeout > 0 and request.user.is_authenticated and not self._is_exempt(request):
            import time

            now = int(time.time())
            last = request.session.get(self.SESSION_KEY)
            if isinstance(last, int) and now - last > timeout:
                return self._expire(request, timeout)
            if not isinstance(last, int) or now - last >= min(30, max(1, timeout // 4)):  # evita gravar a cada clique
                request.session[self.SESSION_KEY] = now
        return self.get_response(request)

    def _is_exempt(self, request):
        from django.urls import Resolver404

        try:
            return resolve(request.path_info).view_name in self.exempt_names
        except Resolver404:
            return False

    def _expire(self, request, timeout):
        from django.contrib import messages
        from django.contrib.auth import logout
        from django.http import JsonResponse
        from django.urls import reverse
        from django.utils.http import urlencode

        from .models import AuthenticationEvent
        from .services import record_authentication_event

        user = request.user
        minutes = max(1, timeout // 60)
        if timeout % 3600 == 0:
            hours = timeout // 3600
            duration = f"{hours} hora" if hours == 1 else f"{hours} horas"
        else:
            duration = "1 minuto" if minutes == 1 else f"{minutes} minutos"
        record_authentication_event(
            AuthenticationEvent.EventType.LOGOUT, request=request, user=user, email=user.email,
            details={"motivo": "inatividade", "minutos_sem_uso": minutes},
        )
        logout(request)
        text = (f"Sua sessão foi encerrada após {duration} sem uso. "
                "Entre novamente com a sua senha.")
        if request.headers.get("X-Requested-With") or "application/json" in request.headers.get("Accept", ""):
            return JsonResponse({"erro": text}, status=401)
        messages.info(request, text)
        login_url = reverse("accounts:login")
        if request.method == "GET":
            login_url += "?" + urlencode({"next": request.get_full_path()})
        return redirect(login_url)

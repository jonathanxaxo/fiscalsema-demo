from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from .authentication import authenticate_request, error_response, record_access


class ApiRequestError(Exception):
    def __init__(self, code, message, status=400):
        self.code, self.message, self.status = code, message, status


@method_decorator(csrf_exempt, name="dispatch")
class ReadOnlyApiView(View):
    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]

    def dispatch(self, request, *args, **kwargs):
        authenticated = authenticate_request(request)
        if isinstance(authenticated, tuple):
            request.api_credential, request.api_actor = authenticated
        else:
            return authenticated
        if request.method != "GET":
            request.api_error_code = "method_not_allowed"
            response = error_response(
                "method_not_allowed", "Esta API permite somente consultas GET.", 405,
                headers={"Allow": "GET"},
            )
            record_access(request, response)
            return response
        try:
            response = super().dispatch(request, *args, **kwargs)
        except ApiRequestError as exc:
            request.api_error_code = exc.code
            response = error_response(exc.code, exc.message, exc.status)
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        record_access(request, response)
        return response

    @staticmethod
    def json(data, status=200):
        return JsonResponse(data, status=status, json_dumps_params={"ensure_ascii": False})


@method_decorator(csrf_exempt, name="dispatch")
class ControlledWriteApiView(View):
    http_method_names = ["get", "post"]
    allowed_methods = {"POST"}

    def dispatch(self, request, *args, **kwargs):
        authenticated = authenticate_request(request)
        if isinstance(authenticated, tuple):
            request.api_credential, request.api_actor = authenticated
        else:
            return authenticated
        if request.method not in self.allowed_methods:
            request.api_error_code = "method_not_allowed"
            response = error_response(
                "method_not_allowed", "Método não permitido nesta rota controlada.",
                405, headers={"Allow": ", ".join(sorted(self.allowed_methods))},
            )
            record_access(request, response)
            return response
        try:
            response = super().dispatch(request, *args, **kwargs)
        except ApiRequestError as exc:
            request.api_error_code = exc.code
            response = error_response(exc.code, exc.message, exc.status)
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        record_access(request, response)
        return response

    @staticmethod
    def json(data, status=200):
        return JsonResponse(data, status=status, json_dumps_params={"ensure_ascii": False})

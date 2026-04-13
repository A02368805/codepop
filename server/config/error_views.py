from django.template.response import TemplateResponse
from django.urls import reverse


def permission_denied(request, exception=None):
    is_authenticated = getattr(request.user, "is_authenticated", False)
    role = getattr(request.user, "role", "")
    return_home_url = reverse("home")
    if is_authenticated and role != "account_user":
        return_home_url = reverse("dashboard")

    return TemplateResponse(
        request,
        "errors/403.html",
        {
            "error_title": "You don't have permission to view this page.",
            "return_home_url": return_home_url,
            "show_sign_in": not is_authenticated,
        },
        status=403,
    )


def page_not_found(request, exception=None):
    return TemplateResponse(
        request,
        "errors/404.html",
        {
            "error_title": "We couldn't find that route.",
            "error_message": "The page may have moved, the link may be stale, or the resource may be outside the active demo flow.",
        },
        status=404,
    )


def server_error(request):
    return TemplateResponse(
        request,
        "errors/500.html",
        {
            "error_title": "Something went wrong on our side.",
            "error_message": "The request reached FloatStack, but the app hit an unexpected error. Try again or return to a stable workflow.",
        },
        status=500,
    )

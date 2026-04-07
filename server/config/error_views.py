from django.template.response import TemplateResponse


def permission_denied(request, exception=None):
    return TemplateResponse(
        request,
        "errors/403.html",
        {
            "error_title": "That page is outside your current scope.",
            "error_message": "FloatStack keeps dashboard and store access on the server. Sign in with the right account or return to a page inside your role.",
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

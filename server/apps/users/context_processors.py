from .selectors import build_brandmark, build_navigation


def navigation(request):
    return {
        "navigation_items": build_navigation(request.user),
        "brandmark": build_brandmark(request.user),
    }

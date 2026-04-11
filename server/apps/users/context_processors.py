from apps.stores.models import Store
from django.conf import settings

from .selectors import build_brandmark, build_navigation

NODE_STORE_CODE_MAPPING = {
    "store-a": "A001",
    "store-b": "B001",
    "store-c": "C001",
}


def _resolve_active_node_context():
    node_id = (getattr(settings, "STORE_ID", "") or "").strip().lower()
    if not node_id:
        return None

    stores = Store.objects.select_related("region").filter(is_active=True)
    expected_store_code = NODE_STORE_CODE_MAPPING.get(node_id, "")
    active_store = (
        stores.filter(store_code=expected_store_code).first()
        if expected_store_code
        else None
    )
    if not active_store:
        active_store = stores.order_by("store_code").first()

    if not active_store:
        return {
            "node_id": node_id,
            "store_name": "",
            "store_code": "",
            "region_code": "",
            "region_name": "",
        }

    return {
        "node_id": node_id,
        "store_name": active_store.name,
        "store_code": active_store.store_code,
        "region_code": active_store.region.code,
        "region_name": active_store.region.name,
    }


def navigation(request):
    return {
        "navigation_items": build_navigation(request.user),
        "brandmark": build_brandmark(request.user),
        "active_node_context": _resolve_active_node_context(),
    }

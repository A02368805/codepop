from apps.users.models import User
from django.db.models import QuerySet

from .models import Region, Store


def stores_visible_to_user(user) -> QuerySet[Store]:
    queryset = Store.objects.select_related("region")
    if not getattr(user, "is_authenticated", False):
        return queryset.none()
    if user.role == User.Role.SUPER_ADMIN:
        return queryset
    if user.role == User.Role.ACCOUNT_USER:
        if user.preferred_store_id:
            return queryset.filter(pk=user.preferred_store_id)
        return queryset.none()
    if user.role == User.Role.LOGISTICS_MANAGER:
        return queryset.filter(
            region__in=user.region_assignments.values("region")
        ).distinct()
    return queryset.filter(user_assignments__user=user).distinct()


def regions_visible_to_user(user) -> QuerySet[Region]:
    queryset = Region.objects.all()
    if not getattr(user, "is_authenticated", False):
        return queryset.none()
    if user.role == User.Role.SUPER_ADMIN:
        return queryset
    if user.role == User.Role.ACCOUNT_USER:
        if user.default_region_id:
            return queryset.filter(pk=user.default_region_id)
        if user.preferred_store_id:
            return queryset.filter(pk=user.preferred_store.region_id)
        return queryset.none()
    if user.role == User.Role.LOGISTICS_MANAGER:
        return queryset.filter(user_assignments__user=user).distinct()
    return queryset.filter(stores__user_assignments__user=user).distinct()


def scoped_region_store_options(user, *, region_id="", store_id=""):
    visible_regions = regions_visible_to_user(user).order_by("name")
    visible_stores = stores_visible_to_user(user).order_by("name")

    selected_region = None
    if region_id:
        selected_region = visible_regions.filter(pk=region_id).first()
        if selected_region:
            visible_stores = visible_stores.filter(region=selected_region)

    selected_store = None
    if store_id:
        selected_store = visible_stores.filter(pk=store_id).first()

    active_store_scope = (
        visible_stores.filter(pk=selected_store.pk)
        if selected_store
        else visible_stores
    )

    return {
        "region_options": visible_regions,
        "store_options": visible_stores,
        "active_store_scope": active_store_scope,
        "selected_region": selected_region,
        "selected_store": selected_store,
    }

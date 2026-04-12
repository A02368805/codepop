from functools import wraps

from apps.stores.models import Region, Store
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.views.generic.base import ContextMixin

from .models import User, UserRegionAssignment, UserStoreAssignment


class RoleRequiredMixin(LoginRequiredMixin):
    allowed_roles: tuple[str, ...] = ()

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if (
            self.allowed_roles
            and getattr(request.user, "role", None) not in self.allowed_roles
        ):
            raise PermissionDenied("You do not have access to this workspace.")
        return response


class GlobalAccessMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not user_has_global_access(request.user):
            raise PermissionDenied("Global access is required for this operation.")
        return super().dispatch(request, *args, **kwargs)


class StoreScopedAccessMixin(LoginRequiredMixin):
    store_kwarg = "store_id"

    def get_scoped_store(self):
        return get_object_or_404(Store, pk=self.kwargs[self.store_kwarg])

    def dispatch(self, request, *args, **kwargs):
        store = self.get_scoped_store()
        if not user_has_store_scope(request.user, store):
            raise PermissionDenied("You do not have store access for this resource.")
        return super().dispatch(request, *args, **kwargs)


class RegionScopedAccessMixin(LoginRequiredMixin):
    region_kwarg = "region_id"

    def get_scoped_region(self):
        return get_object_or_404(Region, pk=self.kwargs[self.region_kwarg])

    def dispatch(self, request, *args, **kwargs):
        region = self.get_scoped_region()
        if not user_has_region_scope(request.user, region):
            raise PermissionDenied("You do not have regional access for this resource.")
        return super().dispatch(request, *args, **kwargs)


class CustomerOrderingRequiredMixin(ContextMixin):
    permission_denied_message = "Drink building and ordering are only available for guests and customer accounts."

    def dispatch(self, request, *args, **kwargs):
        if not user_can_use_customer_ordering(request.user):
            raise PermissionDenied(self.permission_denied_message)
        return super().dispatch(request, *args, **kwargs)


def store_scope_required(store_kwarg="store_id"):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            store = get_object_or_404(Store, pk=kwargs[store_kwarg])
            if not user_has_store_scope(request.user, store):
                raise PermissionDenied(
                    "You do not have store access for this resource."
                )
            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator


def region_scope_required(region_kwarg="region_id"):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            region = get_object_or_404(Region, pk=kwargs[region_kwarg])
            if not user_has_region_scope(request.user, region):
                raise PermissionDenied(
                    "You do not have regional access for this resource."
                )
            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator


def global_access_required(view_func):
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not user_has_global_access(request.user):
            raise PermissionDenied("Global access is required for this operation.")
        return view_func(request, *args, **kwargs)

    return wrapped


def user_has_global_access(user) -> bool:
    return bool(
        getattr(user, "is_authenticated", False) and user.role == User.Role.SUPER_ADMIN
    )


def user_can_use_customer_ordering(user) -> bool:
    if not getattr(user, "is_authenticated", False):
        return True
    return user.role == User.Role.ACCOUNT_USER


def user_has_store_scope(user, store) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    if user_has_global_access(user):
        return True
    return UserStoreAssignment.objects.filter(user=user, store=store).exists()


def user_has_region_scope(user, region) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    if user_has_global_access(user):
        return True
    return UserRegionAssignment.objects.filter(user=user, region=region).exists()


def user_can_manage_store(user, store) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    if user_has_global_access(user):
        return True
    if user.role not in {User.Role.MANAGER, User.Role.ADMIN}:
        return False
    return UserStoreAssignment.objects.filter(user=user, store=store).exists()


def user_can_view_payments_workspace(user) -> bool:
    return bool(
        getattr(user, "is_authenticated", False)
        and user.role in {User.Role.MANAGER, User.Role.SUPER_ADMIN}
    )


def user_can_view_region(user, region) -> bool:
    return user_has_region_scope(user, region)


def user_can_manage_machine(user, machine) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    if user_has_global_access(user):
        return True
    if user.role in {User.Role.MANAGER, User.Role.ADMIN}:
        return user_can_manage_store(user, machine.store)
    if user.role == User.Role.REPAIR_STAFF:
        return UserStoreAssignment.objects.filter(
            user=user, store=machine.store
        ).exists()
    return False


def user_can_approve_transfer(user, transfer) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    if user_has_global_access(user):
        return True
    return user.role == User.Role.LOGISTICS_MANAGER and user_has_region_scope(
        user, transfer.destination_region
    )


def user_can_request_transfer(user, destination_store) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    if user_has_global_access(user):
        return True
    if user.role == User.Role.LOGISTICS_MANAGER:
        return user_has_region_scope(user, destination_store.region)
    return user_can_manage_store(user, destination_store)


def user_can_progress_transfer(user, transfer) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    if user_has_global_access(user):
        return True
    if user.role == User.Role.LOGISTICS_MANAGER:
        destination_allowed = user_has_region_scope(user, transfer.destination_region)
        source_allowed = (
            transfer.source_store
            and user_has_region_scope(user, transfer.source_store.region)
        ) or (
            transfer.source_hub
            and user_has_region_scope(user, transfer.source_hub.region)
        )
        return bool(destination_allowed or source_allowed)
    if user.role in {User.Role.MANAGER, User.Role.ADMIN}:
        return bool(
            user_can_manage_store(user, transfer.destination_store)
            or (
                transfer.source_store
                and user_can_manage_store(user, transfer.source_store)
            )
        )
    return False


def user_can_receive_transfer(user, transfer) -> bool:
    if user_can_progress_transfer(user, transfer):
        return True
    return (
        getattr(user, "is_authenticated", False)
        and user.role in {User.Role.MANAGER, User.Role.ADMIN}
        and user_can_manage_store(user, transfer.destination_store)
    )


def user_can_manage_supplier_order(user, store) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    if user_has_global_access(user):
        return True
    return user.role == User.Role.LOGISTICS_MANAGER and user_has_region_scope(
        user, store.region
    )

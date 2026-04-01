from __future__ import annotations

from apps.sync.services import create_audit_log, serialize_instance
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.urls import reverse

from .models import FavoriteDrink, TastePreference, User, UserStoreAssignment
from .permissions import user_can_manage_store, user_has_global_access
from .selectors import get_dashboard_route_name


def get_effective_role(user):
    if not getattr(user, "is_authenticated", False):
        return None
    return getattr(user, "role", None)


def get_post_login_url(user) -> str:
    role = get_effective_role(user)
    if role is None:
        return reverse("home")
    if role == User.Role.ACCOUNT_USER:
        return reverse("orders:recommendations")
    return reverse(get_dashboard_route_name(role))


def save_preference_profile(
    *,
    user,
    favorite_sodas=None,
    favorite_syrups=None,
    favorite_add_ins=None,
    favorite_ice_creams=None,
    disliked_ingredients=None,
    dietary_preferences=None,
    sweetness_preference=None,
    adventurousness_preference=None,
):
    favorite_sodas = {
        token.strip().lower() for token in (favorite_sodas or []) if token.strip()
    }
    favorite_syrups = {
        token.strip().lower() for token in (favorite_syrups or []) if token.strip()
    }
    favorite_add_ins = {
        token.strip().lower() for token in (favorite_add_ins or []) if token.strip()
    }
    favorite_ice_creams = {
        token.strip().lower() for token in (favorite_ice_creams or []) if token.strip()
    }
    disliked_ingredients = {
        token.strip().lower() for token in (disliked_ingredients or []) if token.strip()
    }
    dietary_preferences = {
        token.strip().lower() for token in (dietary_preferences or []) if token.strip()
    }

    TastePreference.objects.filter(user=user).delete()

    for ingredient_name in favorite_sodas:
        TastePreference.objects.create(
            user=user,
            ingredient_name=ingredient_name,
            preference_type=TastePreference.PreferenceType.FAVORITE_SODA,
        )

    for ingredient_name in favorite_syrups:
        TastePreference.objects.create(
            user=user,
            ingredient_name=ingredient_name,
            preference_type=TastePreference.PreferenceType.FAVORITE_SYRUP,
        )

    for ingredient_name in favorite_add_ins:
        TastePreference.objects.create(
            user=user,
            ingredient_name=ingredient_name,
            preference_type=TastePreference.PreferenceType.FAVORITE_ADD_IN,
        )

    for ingredient_name in favorite_ice_creams:
        TastePreference.objects.create(
            user=user,
            ingredient_name=ingredient_name,
            preference_type=TastePreference.PreferenceType.FAVORITE_ICE_CREAM,
        )

    for ingredient_name in disliked_ingredients:
        TastePreference.objects.create(
            user=user,
            ingredient_name=ingredient_name,
            preference_type=TastePreference.PreferenceType.DISLIKE,
        )

    for ingredient_name in dietary_preferences:
        TastePreference.objects.create(
            user=user,
            ingredient_name=ingredient_name,
            preference_type=TastePreference.PreferenceType.DIETARY,
        )

    user.sweetness_preference = (
        sweetness_preference or user.SweetnessPreference.BALANCED
    )
    user.adventurousness_preference = (
        adventurousness_preference or user.AdventurousnessPreference.BALANCED
    )
    user.save(
        update_fields=[
            "sweetness_preference",
            "adventurousness_preference",
            "updated_at",
        ]
    )

    from apps.analytics.tasks import refresh_account_recommendations

    transaction.on_commit(
        lambda: refresh_account_recommendations.delay(
            str(user.pk),
            reason="Your saved FloatStack taste profile was updated",
        )
    )


def save_favorite_drink(
    *,
    user,
    name,
    recipe_key,
    size_snapshot,
    base_price_snapshot,
    customizations_json,
    description="",
):
    favorite, _ = FavoriteDrink.objects.update_or_create(
        user=user,
        name=name,
        defaults={
            "recipe_key": recipe_key,
            "size_snapshot": size_snapshot,
            "base_price_snapshot": base_price_snapshot,
            "customizations_json": customizations_json,
            "description": description,
        },
    )
    return favorite


def remove_favorite_drink(*, user, favorite):
    favorite.delete()


def update_scoped_user(*, actor, target_user, role, status):
    if actor == target_user and not user_has_global_access(actor):
        raise PermissionDenied("You cannot change your own account scope here.")

    if user_has_global_access(actor):
        allowed = True
        scoped_store = None
    else:
        scoped_store = (
            actor.store_assignments.select_related("store").first().store
            if actor.store_assignments.exists()
            else None
        )
        allowed = bool(scoped_store and user_can_manage_store(actor, scoped_store))

    if not allowed:
        raise PermissionDenied("This user is outside your management scope.")
    if role not in {User.Role.ACCOUNT_USER, User.Role.MANAGER, User.Role.ADMIN}:
        raise PermissionDenied(
            "This role cannot be assigned from the store admin panel."
        )

    before = serialize_instance(target_user)
    target_user.role = role
    target_user.status = status
    if scoped_store and role in {User.Role.MANAGER, User.Role.ADMIN}:
        assignment_type = (
            UserStoreAssignment.AssignmentType.MANAGER_SCOPE
            if role == User.Role.MANAGER
            else UserStoreAssignment.AssignmentType.ADMIN_SCOPE
        )
        UserStoreAssignment.objects.filter(
            user=target_user,
            store=scoped_store,
            assignment_type__in=[
                UserStoreAssignment.AssignmentType.MANAGER_SCOPE,
                UserStoreAssignment.AssignmentType.ADMIN_SCOPE,
            ],
        ).exclude(assignment_type=assignment_type).delete()
        UserStoreAssignment.objects.get_or_create(
            user=target_user,
            store=scoped_store,
            assignment_type=assignment_type,
        )
        target_user.preferred_store = target_user.preferred_store or scoped_store
        target_user.default_region = target_user.default_region or scoped_store.region
    elif scoped_store and role == User.Role.ACCOUNT_USER:
        UserStoreAssignment.objects.filter(
            user=target_user, store=scoped_store
        ).delete()
    target_user.save()
    create_audit_log(
        actor=actor,
        action="user.scoped_update",
        instance=target_user,
        before=before,
        after=serialize_instance(target_user),
    )
    return target_user

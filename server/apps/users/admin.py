from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import (
    FavoriteDrink,
    TastePreference,
    User,
    UserRegionAssignment,
    UserStoreAssignment,
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "email",
        "role",
        "status",
        "preferred_store",
        "default_region",
        "is_staff",
    )
    list_filter = ("role", "status", "is_staff", "is_superuser")
    ordering = ("email",)
    search_fields = ("email", "first_name", "last_name")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Identity",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "username",
                    "phone_number",
                )
            },
        ),
        (
            "FloatStack Access",
            {
                "fields": (
                    "role",
                    "status",
                    "preferred_store",
                    "default_region",
                    "is_email_verified",
                )
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            "Important dates",
            {"fields": ("last_login", "date_joined", "created_at", "updated_at")},
        ),
    )
    readonly_fields = ("created_at", "updated_at")
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2", "role", "status"),
            },
        ),
    )


@admin.register(UserStoreAssignment)
class UserStoreAssignmentAdmin(admin.ModelAdmin):
    list_display = ("user", "store", "assignment_type", "created_at")
    list_filter = ("assignment_type", "store__region")
    search_fields = ("user__email", "store__name")


@admin.register(UserRegionAssignment)
class UserRegionAssignmentAdmin(admin.ModelAdmin):
    list_display = ("user", "region", "assignment_type", "created_at")
    list_filter = ("assignment_type", "region")
    search_fields = ("user__email", "region__name")


@admin.register(TastePreference)
class TastePreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "ingredient_name", "preference_type", "updated_at")
    list_filter = ("preference_type",)
    search_fields = ("user__email", "ingredient_name")


@admin.register(FavoriteDrink)
class FavoriteDrinkAdmin(admin.ModelAdmin):
    list_display = ("user", "name", "recipe_key", "size_snapshot", "last_ordered_at")
    search_fields = ("user__email", "name", "recipe_key")

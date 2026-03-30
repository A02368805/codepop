import uuid

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("The email address must be set.")

        email = self.normalize_email(email)
        extra_fields.setdefault("username", email.split("@")[0])
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", User.Role.ACCOUNT_USER)
        extra_fields.setdefault("status", User.Status.ACTIVE)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("role", User.Role.SUPER_ADMIN)
        extra_fields.setdefault("status", User.Status.ACTIVE)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        ACCOUNT_USER = "account_user", _("Account User")
        MANAGER = "manager", _("Manager")
        ADMIN = "admin", _("Admin")
        LOGISTICS_MANAGER = "logistics_manager", _("Logistics Manager")
        REPAIR_STAFF = "repair_staff", _("Repair Staff")
        SUPER_ADMIN = "super_admin", _("Super Admin")

    class Status(models.TextChoices):
        ACTIVE = "active", _("Active")
        LOCKED = "locked", _("Locked")
        DISABLED = "disabled", _("Disabled")
        PENDING = "pending", _("Pending")

    class SweetnessPreference(models.TextChoices):
        LIGHT = "light", _("Light Sweetness")
        BALANCED = "balanced", _("Balanced Sweetness")
        SWEET = "sweet", _("Sweet")
        EXTRA_SWEET = "extra_sweet", _("Extra Sweet")

    class AdventurousnessPreference(models.TextChoices):
        CLASSIC = "classic", _("Keep It Classic")
        BALANCED = "balanced", _("Balanced")
        ADVENTUROUS = "adventurous", _("Adventurous")

    STAFF_ROLES = {
        Role.MANAGER,
        Role.ADMIN,
        Role.LOGISTICS_MANAGER,
        Role.REPAIR_STAFF,
        Role.SUPER_ADMIN,
    }

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=150, blank=True)
    email = models.EmailField(unique=True)
    role = models.CharField(
        max_length=32, choices=Role.choices, default=Role.ACCOUNT_USER
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.ACTIVE
    )
    phone_number = models.CharField(max_length=32, blank=True)
    preferred_store = models.ForeignKey(
        "stores.Store",
        related_name="preferred_by_users",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    default_region = models.ForeignKey(
        "stores.Region",
        related_name="defaulted_by_users",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    sweetness_preference = models.CharField(
        max_length=24,
        choices=SweetnessPreference.choices,
        default=SweetnessPreference.BALANCED,
    )
    adventurousness_preference = models.CharField(
        max_length=24,
        choices=AdventurousnessPreference.choices,
        default=AdventurousnessPreference.BALANCED,
    )
    is_email_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def save(self, *args, **kwargs):
        if not self.username:
            self.username = self.email
        self.is_staff = self.role in self.STAFF_ROLES or self.is_superuser
        self.is_active = self.status == self.Status.ACTIVE
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email


class UserStoreAssignment(models.Model):
    class AssignmentType(models.TextChoices):
        PRIMARY = "primary", _("Primary")
        SECONDARY = "secondary", _("Secondary")
        REPAIR_SCOPE = "repair_scope", _("Repair Scope")
        ADMIN_SCOPE = "admin_scope", _("Admin Scope")
        MANAGER_SCOPE = "manager_scope", _("Manager Scope")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "users.User", related_name="store_assignments", on_delete=models.CASCADE
    )
    store = models.ForeignKey(
        "stores.Store", related_name="user_assignments", on_delete=models.CASCADE
    )
    assignment_type = models.CharField(
        max_length=32, choices=AssignmentType.choices, default=AssignmentType.PRIMARY
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "store", "assignment_type")
        ordering = ("store__name", "assignment_type")

    def __str__(self):
        return f"{self.user.email} -> {self.store.name} ({self.assignment_type})"


class UserRegionAssignment(models.Model):
    class AssignmentType(models.TextChoices):
        LOGISTICS_SCOPE = "logistics_scope", _("Logistics Scope")
        OVERSIGHT_SCOPE = "oversight_scope", _("Oversight Scope")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "users.User", related_name="region_assignments", on_delete=models.CASCADE
    )
    region = models.ForeignKey(
        "stores.Region", related_name="user_assignments", on_delete=models.CASCADE
    )
    assignment_type = models.CharField(
        max_length=32,
        choices=AssignmentType.choices,
        default=AssignmentType.LOGISTICS_SCOPE,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "region", "assignment_type")
        ordering = ("region__name", "assignment_type")

    def __str__(self):
        return f"{self.user.email} -> {self.region.name} ({self.assignment_type})"


class TastePreference(models.Model):
    class PreferenceType(models.TextChoices):
        LIKE = "like", _("Like")
        DISLIKE = "dislike", _("Dislike")
        FAVORITE_SODA = "favorite_soda", _("Favorite Soda")
        FAVORITE_SYRUP = "favorite_syrup", _("Favorite Syrup")
        FAVORITE_ADD_IN = "favorite_add_in", _("Favorite Add-In")
        FAVORITE_ICE_CREAM = "favorite_ice_cream", _("Favorite Ice Cream")
        DIETARY = "dietary", _("Dietary Preference")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "users.User", related_name="taste_preferences", on_delete=models.CASCADE
    )
    ingredient_name = models.CharField(max_length=80)
    preference_type = models.CharField(
        max_length=32, choices=PreferenceType.choices, default=PreferenceType.LIKE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "ingredient_name", "preference_type")
        ordering = ("ingredient_name", "preference_type")

    def save(self, *args, **kwargs):
        self.ingredient_name = self.ingredient_name.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.email} / {self.preference_type} / {self.ingredient_name}"


class FavoriteDrink(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "users.User", related_name="favorite_drinks", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=120)
    recipe_key = models.SlugField(blank=True)
    size_snapshot = models.CharField(max_length=24, default="medium")
    base_price_snapshot = models.DecimalField(max_digits=10, decimal_places=2)
    customizations_json = models.JSONField(default=dict, blank=True)
    description = models.TextField(blank=True)
    last_ordered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "name")
        ordering = ("name",)

    def __str__(self):
        return f"{self.user.email} / {self.name}"

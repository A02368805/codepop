from apps.orders.catalog import (
    ADD_IN_OPTIONS,
    ADVENTUROUSNESS_PREFERENCE_CHOICES,
    DIETARY_PREFERENCE_OPTIONS,
    ICE_CREAM_OPTIONS,
    SODA_OPTIONS,
    SWEETNESS_PREFERENCE_CHOICES,
    SYRUP_OPTIONS,
    combined_ingredient_choices,
)
from apps.stores.models import Store
from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm

from .models import User


class EmailAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Email"
        self.fields["username"].widget.attrs.update(
            {"placeholder": "you@floatstack.example", "autocomplete": "email"}
        )
        self.fields["password"].widget.attrs.update(
            {"placeholder": "Your password", "autocomplete": "current-password"}
        )


class RegistrationForm(forms.ModelForm):
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"})
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"})
    )
    preferred_store = forms.ModelChoiceField(
        queryset=Store.objects.filter(is_active=True).order_by("name"),
        required=False,
        empty_label="Choose later",
    )

    class Meta:
        model = User
        fields = ("email", "first_name", "last_name", "preferred_store")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account already exists for that email.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", "Passwords must match.")
        if password1:
            try:
                password_validation.validate_password(password1)
            except forms.ValidationError as exc:
                self.add_error("password1", exc)
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.ACCOUNT_USER
        user.status = User.Status.ACTIVE
        user.default_region = (
            user.preferred_store.region if user.preferred_store_id else None
        )
        user.is_email_verified = True
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class PreferenceProfileForm(forms.Form):
    favorite_sodas = forms.MultipleChoiceField(
        required=False,
        choices=[(key, value["label"]) for key, value in SODA_OPTIONS.items()],
        widget=forms.CheckboxSelectMultiple,
        help_text="Choose every base soda you want CodePop AI to prefer.",
    )
    favorite_syrups = forms.MultipleChoiceField(
        required=False,
        choices=[(key, value["label"]) for key, value in SYRUP_OPTIONS.items()],
        widget=forms.CheckboxSelectMultiple,
        help_text="Pick the flavor shots you reach for most often.",
    )
    favorite_add_ins = forms.MultipleChoiceField(
        required=False,
        choices=[(key, value["label"]) for key, value in ADD_IN_OPTIONS.items()],
        widget=forms.CheckboxSelectMultiple,
        help_text="Choose creamy, fresh, and finishing add-ins you usually enjoy.",
    )
    favorite_ice_creams = forms.MultipleChoiceField(
        required=False,
        choices=[(key, value["label"]) for key, value in ICE_CREAM_OPTIONS.items()],
        widget=forms.CheckboxSelectMultiple,
        help_text="These are used when AI decides a float-style topper makes sense.",
    )
    disliked_ingredients = forms.MultipleChoiceField(
        required=False,
        choices=combined_ingredient_choices(),
        widget=forms.CheckboxSelectMultiple,
        help_text="Anything here will be actively avoided in recommendations when possible.",
    )
    dietary_preferences = forms.MultipleChoiceField(
        required=False,
        choices=DIETARY_PREFERENCE_OPTIONS,
        widget=forms.CheckboxSelectMultiple,
        help_text="Optional constraints that shape AI suggestions and fills.",
    )
    sweetness_preference = forms.ChoiceField(
        choices=SWEETNESS_PREFERENCE_CHOICES,
        help_text="Tell CodePop whether to keep recommendations lighter or sweeter.",
    )
    adventurousness_preference = forms.ChoiceField(
        choices=ADVENTUROUSNESS_PREFERENCE_CHOICES,
        help_text="Classic keeps things safer. Adventurous opens the door to bolder combinations.",
    )

    def clean(self):
        cleaned_data = super().clean()
        favorite_sodas = set(cleaned_data.get("favorite_sodas") or [])
        favorite_syrups = set(cleaned_data.get("favorite_syrups") or [])
        favorite_add_ins = set(cleaned_data.get("favorite_add_ins") or [])
        favorite_ice_creams = set(cleaned_data.get("favorite_ice_creams") or [])
        disliked_ingredients = set(cleaned_data.get("disliked_ingredients") or [])
        overlap = (
            favorite_sodas | favorite_syrups | favorite_add_ins | favorite_ice_creams
        ) & disliked_ingredients
        if overlap:
            raise forms.ValidationError(
                f"You selected the same option in both lists: {', '.join(sorted(overlap))}."
            )
        return cleaned_data


class ScopedUserUpdateForm(forms.Form):
    role = forms.ChoiceField(
        choices=[
            (User.Role.ACCOUNT_USER, "Account User"),
            (User.Role.MANAGER, "Manager"),
            (User.Role.ADMIN, "Admin"),
        ]
    )
    status = forms.ChoiceField(choices=User.Status.choices)

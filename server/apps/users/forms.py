import re

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
        label="Enter password",
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "new-password",
                "placeholder": "Create a password",
            }
        ),
    )
    password2 = forms.CharField(
        label="Re-enter password",
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "new-password",
                "placeholder": "Re-enter password",
            }
        ),
    )
    preferred_store = forms.ModelChoiceField(
        queryset=Store.objects.filter(is_active=True).order_by("name"),
        required=False,
        empty_label="Choose later",
    )

    class Meta:
        model = User
        fields = ("email", "first_name", "last_name", "preferred_store")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].help_text = ""

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
            if not (re.search(r"[A-Za-z]", password1) and re.search(r"\d", password1)):
                self.add_error(
                    "password1",
                    "Password must include at least one letter and one number.",
                )
            try:
                password_validation.validate_password(password1)
            except forms.ValidationError as exc:
                clarified_errors = []
                for message in exc.messages:
                    lower_message = message.lower()
                    if "too common" in lower_message:
                        clarified_errors.append(
                            "This password is too common and easy to guess. "
                            "Choose a less common phrase with a mix of letters and numbers."
                        )
                    elif "entirely numeric" in lower_message:
                        clarified_errors.append(
                            "Password cannot be only numbers. Include letters too."
                        )
                    else:
                        clarified_errors.append(message)
                for clarified_message in clarified_errors:
                    self.add_error("password1", clarified_message)
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
    preferred_store = forms.ModelChoiceField(
        queryset=Store.objects.filter(is_active=True).order_by("name"),
        required=False,
        empty_label="No preferred store",
        help_text="Set a default store so recommendations and flows start in the right place.",
    )
    favorite_sodas = forms.MultipleChoiceField(
        required=False,
        choices=[(key, value["label"]) for key, value in SODA_OPTIONS.items()],
        widget=forms.CheckboxSelectMultiple,
        help_text="Choose every base soda you want FloatStack AI to prefer.",
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
        required=False,
        initial=User.SweetnessPreference.BALANCED,
        help_text="Tell FloatStack whether to keep recommendations lighter or sweeter.",
    )
    adventurousness_preference = forms.ChoiceField(
        choices=ADVENTUROUSNESS_PREFERENCE_CHOICES,
        required=False,
        initial=User.AdventurousnessPreference.BALANCED,
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
            cleaned_data["disliked_ingredients"] = sorted(
                disliked_ingredients - overlap
            )

        sweetness = cleaned_data.get("sweetness_preference")
        adventurousness = cleaned_data.get("adventurousness_preference")
        sweetness_values = {value for value, _ in SWEETNESS_PREFERENCE_CHOICES}
        adventurousness_values = {
            value for value, _ in ADVENTUROUSNESS_PREFERENCE_CHOICES
        }
        cleaned_data["sweetness_preference"] = (
            sweetness
            if sweetness in sweetness_values
            else User.SweetnessPreference.BALANCED
        )
        cleaned_data["adventurousness_preference"] = (
            adventurousness
            if adventurousness in adventurousness_values
            else User.AdventurousnessPreference.BALANCED
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

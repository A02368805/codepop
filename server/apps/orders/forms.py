from django import forms
from django.utils import timezone

from .catalog import (
    ADD_IN_OPTIONS,
    ICE_CREAM_OPTIONS,
    SIZE_LABELS,
    SODA_OPTIONS,
    SYRUP_OPTIONS,
    get_menu_item,
)
from .pickup import parse_pickup_choice, pickup_time_choices


class DrinkCustomizationForm(forms.Form):
    size = forms.ChoiceField(
        choices=[(key, label) for key, label in SIZE_LABELS.items()],
        widget=forms.RadioSelect,
    )
    soda = forms.ChoiceField(
        choices=[(key, value["label"]) for key, value in SODA_OPTIONS.items()],
        widget=forms.RadioSelect,
    )
    syrups = forms.MultipleChoiceField(
        required=False,
        widget=forms.CheckboxSelectMultiple,
        choices=[(key, value["label"]) for key, value in SYRUP_OPTIONS.items()],
    )
    add_ins = forms.MultipleChoiceField(
        required=False,
        widget=forms.CheckboxSelectMultiple,
        choices=[(key, value["label"]) for key, value in ADD_IN_OPTIONS.items()],
    )
    ice_cream = forms.ChoiceField(
        required=False,
        label="Ice cream",
        choices=[("", "No ice cream")]
        + [(key, value["label"]) for key, value in ICE_CREAM_OPTIONS.items()],
        widget=forms.RadioSelect,
    )
    quantity = forms.IntegerField(min_value=1, max_value=12, initial=1)
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))

    def __init__(self, *args, drink_slug=None, **kwargs):
        super().__init__(*args, **kwargs)
        if drink_slug:
            menu_item = get_menu_item(drink_slug)
            self.initial.setdefault("size", "medium")
            self.initial.setdefault("soda", menu_item["default_soda"])
            self.initial.setdefault("syrups", menu_item["default_syrups"])
            self.initial.setdefault("add_ins", menu_item["default_add_ins"])
            self.initial.setdefault("ice_cream", menu_item.get("default_ice_cream", ""))


class CartQuantityForm(forms.Form):
    quantity = forms.IntegerField(min_value=0, max_value=12)


class CheckoutForm(forms.Form):
    pickup_time_choice = forms.ChoiceField(
        required=False,
        label="Pickup time",
        choices=[],
    )
    guest_name = forms.CharField(required=False)
    guest_email = forms.EmailField(required=False)
    guest_phone_number = forms.CharField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["pickup_time_choice"].choices = pickup_time_choices()

    def clean(self):
        cleaned_data = super().clean()
        pickup_time_requested = parse_pickup_choice(
            cleaned_data.get("pickup_time_choice"),
        )
        if pickup_time_requested and pickup_time_requested <= timezone.now():
            self.add_error("pickup_time_choice", "Pickup time must be in the future.")
        cleaned_data["pickup_time_requested"] = pickup_time_requested
        return cleaned_data


class GuestLookupForm(forms.Form):
    lookup_code = forms.CharField(max_length=24)


class MenuAiPromptForm(forms.Form):
    prompt = forms.CharField(
        max_length=500,
        widget=forms.Textarea(
            attrs={
                "rows": 4,
                "placeholder": "Tell FloatStack what kind of drink you want, like fruity, creamy, caffeine-free, or bold.",
                "id": "menu-ai-prompt",
            }
        ),
    )

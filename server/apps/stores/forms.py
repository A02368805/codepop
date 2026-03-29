from apps.orders.pickup import parse_pickup_choice, pickup_time_choices
from django import forms
from django.utils import timezone

from .location import geocode_location_query


class StoreRecommendationForm(forms.Form):
    location_query = forms.CharField(
        required=False,
        label="ZIP code or address",
        widget=forms.TextInput(
            attrs={"placeholder": "Enter a ZIP code or street address"}
        ),
    )
    latitude = forms.DecimalField(
        required=False, decimal_places=6, max_digits=9, widget=forms.HiddenInput()
    )
    longitude = forms.DecimalField(
        required=False, decimal_places=6, max_digits=9, widget=forms.HiddenInput()
    )
    pickup_time_choice = forms.ChoiceField(
        required=False,
        label="Suggested pickup time",
        choices=[],
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["pickup_time_choice"].choices = pickup_time_choices()

    def clean(self):
        cleaned_data = super().clean()
        location_query = cleaned_data.get("location_query", "").strip()
        latitude = cleaned_data.get("latitude")
        longitude = cleaned_data.get("longitude")
        pickup_time_requested = parse_pickup_choice(
            cleaned_data.get("pickup_time_choice"),
        )

        if location_query and (latitude is None or longitude is None):
            geocoded = geocode_location_query(location_query)
            if geocoded:
                cleaned_data["latitude"] = latitude = geocoded["latitude"]
                cleaned_data["longitude"] = longitude = geocoded["longitude"]

        if (latitude is None) != (longitude is None):
            raise forms.ValidationError(
                "We couldn't place that location yet. Try a ZIP code, use your device location, or choose a store manually."
            )
        if latitude is not None and not (-90 <= latitude <= 90):
            self.add_error("location_query", "The resolved location was invalid.")
        if longitude is not None and not (-180 <= longitude <= 180):
            self.add_error("location_query", "The resolved location was invalid.")
        if pickup_time_requested and pickup_time_requested <= timezone.now():
            self.add_error("pickup_time_choice", "Pickup time must be in the future.")
        cleaned_data["pickup_time_requested"] = pickup_time_requested
        return cleaned_data

import uuid

from django.db import models

from .location import apple_maps_url, google_maps_url, mapbox_static_map_url


class Region(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=1, unique=True)
    name = models.CharField(max_length=120)
    hub_city = models.CharField(max_length=80)
    hub_state_code = models.CharField(max_length=2)
    center_latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    center_longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("code",)

    def __str__(self):
        return f"{self.code} - {self.name}"


class Store(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    region = models.ForeignKey(
        "stores.Region", related_name="stores", on_delete=models.PROTECT
    )
    slug = models.SlugField(unique=True)
    store_code = models.CharField(max_length=16, unique=True)
    name = models.CharField(max_length=120)
    city = models.CharField(max_length=80)
    state_code = models.CharField(max_length=2)
    address_line_1 = models.CharField(max_length=255)
    postal_code = models.CharField(max_length=12)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    timezone = models.CharField(max_length=64, default="America/Denver")
    contact_email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("region__code", "store_code")

    def __str__(self):
        return f"{self.store_code} - {self.name}"

    @property
    def full_address(self) -> str:
        return (
            f"{self.address_line_1}, {self.city}, {self.state_code} {self.postal_code}"
        )

    @property
    def customer_label(self) -> str:
        return self.name

    @property
    def google_maps_url(self) -> str:
        return google_maps_url(self.full_address)

    @property
    def apple_maps_url(self) -> str:
        return apple_maps_url(self.full_address)

    @property
    def mapbox_static_map_url(self) -> str:
        return mapbox_static_map_url(
            latitude=self.latitude,
            longitude=self.longitude,
        )

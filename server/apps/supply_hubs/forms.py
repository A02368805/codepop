from decimal import Decimal

from apps.inventory.models import InventoryItem, LocalSupplier
from apps.stores.models import Store
from apps.stores.selectors import regions_visible_to_user, stores_visible_to_user
from apps.stores.utils import haversine_miles
from django import forms

from .models import SupplyHub


class TransferRequestForm(forms.Form):
    SOURCE_KIND_AUTO = "auto"
    SOURCE_KIND_STORE = "store"
    SOURCE_KIND_HUB = "hub"
    SOURCE_KIND_CHOICES = (
        (SOURCE_KIND_AUTO, "Smart source"),
        (SOURCE_KIND_STORE, "Specific store"),
        (SOURCE_KIND_HUB, "Specific hub"),
    )

    destination_store = forms.ModelChoiceField(queryset=Store.objects.none())
    inventory_item = forms.ModelChoiceField(queryset=InventoryItem.objects.none())
    quantity_requested = forms.DecimalField(
        decimal_places=2,
        max_digits=12,
        min_value=Decimal("1.00"),
    )
    source_kind = forms.ChoiceField(
        choices=SOURCE_KIND_CHOICES, initial=SOURCE_KIND_AUTO
    )
    source_store = forms.ModelChoiceField(queryset=Store.objects.none(), required=False)
    source_hub = forms.ModelChoiceField(
        queryset=SupplyHub.objects.none(), required=False
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        visible_stores = list(
            stores_visible_to_user(user).select_related("region").order_by("name")
        )
        visible_store_ids = [store.id for store in visible_stores]
        visible_regions = list(regions_visible_to_user(user).order_by("name"))
        visible_region_ids = {region.id for region in visible_regions}

        hub_ids = []
        for hub in (
            SupplyHub.objects.filter(is_active=True)
            .select_related("region")
            .order_by("name")
        ):
            if hub.region_id in visible_region_ids:
                hub_ids.append(hub.id)
                continue
            if any(
                haversine_miles(
                    hub.latitude, hub.longitude, store.latitude, store.longitude
                )
                <= Decimal("1000")
                for store in visible_stores
            ):
                hub_ids.append(hub.id)

        self.fields["destination_store"].queryset = Store.objects.filter(
            id__in=visible_store_ids
        ).select_related("region")
        self.fields["source_store"].queryset = Store.objects.filter(
            id__in=visible_store_ids
        ).select_related("region")
        self.fields["source_hub"].queryset = SupplyHub.objects.filter(
            id__in=hub_ids
        ).select_related("region")
        self.fields["inventory_item"].queryset = InventoryItem.objects.filter(
            is_active=True
        ).order_by("category", "name")

        self.fields["destination_store"].label = "Destination store"
        self.fields["inventory_item"].label = "Inventory item"
        self.fields["quantity_requested"].label = "Requested quantity"
        self.fields["source_kind"].label = "Source selection"
        self.fields["source_store"].label = "Source store"
        self.fields["source_hub"].label = "Source hub"

    def clean(self):
        cleaned_data = super().clean()
        destination_store = cleaned_data.get("destination_store")
        source_kind = cleaned_data.get("source_kind")
        source_store = cleaned_data.get("source_store")
        source_hub = cleaned_data.get("source_hub")

        if source_kind == self.SOURCE_KIND_STORE and not source_store:
            self.add_error("source_store", "Choose a source store.")
        if source_kind == self.SOURCE_KIND_HUB and not source_hub:
            self.add_error("source_hub", "Choose a source hub.")
        if destination_store and source_store and destination_store == source_store:
            self.add_error(
                "source_store", "Source and destination must be different stores."
            )
        if (
            destination_store
            and source_store
            and destination_store.region_id != source_store.region_id
        ):
            self.add_error(
                "source_store",
                "Direct store transfers must stay within the same region.",
            )
        return cleaned_data


class SupplierOrderForm(forms.Form):
    store = forms.ModelChoiceField(queryset=Store.objects.none())
    supplier = forms.ModelChoiceField(queryset=LocalSupplier.objects.none())
    inventory_item = forms.ModelChoiceField(queryset=InventoryItem.objects.none())
    quantity_requested = forms.DecimalField(
        decimal_places=2,
        max_digits=12,
        min_value=Decimal("1.00"),
    )
    expected_delivery_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    unit_cost = forms.DecimalField(
        required=False,
        decimal_places=2,
        max_digits=10,
        min_value=Decimal("0.00"),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        visible_regions = regions_visible_to_user(user)
        visible_stores = stores_visible_to_user(user).order_by("name")
        self.fields["store"].queryset = visible_stores
        self.fields["supplier"].queryset = LocalSupplier.objects.filter(
            is_active=True,
            service_region__in=visible_regions,
        ).order_by("name")
        self.fields["inventory_item"].queryset = InventoryItem.objects.filter(
            is_active=True
        ).order_by("category", "name")

        self.fields["quantity_requested"].label = "Bulk quantity"
        self.fields["expected_delivery_date"].label = "Expected delivery"

    def clean(self):
        cleaned_data = super().clean()
        store = cleaned_data.get("store")
        supplier = cleaned_data.get("supplier")
        if (
            store
            and supplier
            and supplier.service_region_id
            and supplier.service_region_id != store.region_id
        ):
            self.add_error(
                "supplier",
                "That supplier is not configured for the selected store region.",
            )
        return cleaned_data

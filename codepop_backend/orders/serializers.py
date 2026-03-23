from rest_framework import serializers

from .models import (
    HubInventoryBalance,
    InventoryItem,
    Region,
    RestockAlert,
    Store,
    StoreInventoryBalance,
    SupplyHub,
    SupplyTransfer,
)


class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = ["id", "name", "code"]


class StoreSerializer(serializers.ModelSerializer):
    region = RegionSerializer(read_only=True)

    class Meta:
        model = Store
        fields = ["id", "name", "region"]


class SupplyHubSerializer(serializers.ModelSerializer):
    region = RegionSerializer(read_only=True)

    class Meta:
        model = SupplyHub
        fields = ["id", "name", "region"]


class InventoryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryItem
        fields = ["id", "name", "item_type", "unit"]


class StoreInventoryBalanceSerializer(serializers.ModelSerializer):
    store = StoreSerializer(read_only=True)
    item = InventoryItemSerializer(read_only=True)

    class Meta:
        model = StoreInventoryBalance
        fields = ["id", "store", "item", "quantity", "threshold", "updated_at"]


class HubInventoryBalanceSerializer(serializers.ModelSerializer):
    hub = SupplyHubSerializer(read_only=True)
    item = InventoryItemSerializer(read_only=True)

    class Meta:
        model = HubInventoryBalance
        fields = ["id", "hub", "item", "quantity", "updated_at"]


class RestockAlertSerializer(serializers.ModelSerializer):
    store = StoreSerializer(read_only=True)
    item = InventoryItemSerializer(read_only=True)

    class Meta:
        model = RestockAlert
        fields = [
            "id",
            "store",
            "item",
            "status",
            "severity",
            "message",
            "created_at",
            "resolved_at",
        ]


class SupplyTransferSerializer(serializers.ModelSerializer):
    source_store = StoreSerializer(read_only=True)
    source_hub = SupplyHubSerializer(read_only=True)
    destination_store = StoreSerializer(read_only=True)
    item = InventoryItemSerializer(read_only=True)

    class Meta:
        model = SupplyTransfer
        fields = [
            "id",
            "source_store",
            "source_hub",
            "destination_store",
            "item",
            "quantity",
            "status",
            "requested_by",
            "approved_by",
            "created_at",
            "approved_at",
            "completed_at",
            "note",
        ]


class SupplyTransferCreateSerializer(serializers.Serializer):
    source_store_id = serializers.IntegerField(required=False)
    source_hub_id = serializers.IntegerField(required=False)
    destination_store_id = serializers.IntegerField(required=True)
    item_id = serializers.IntegerField(required=True)
    quantity = serializers.IntegerField(min_value=1)
    note = serializers.CharField(required=False, allow_blank=True, max_length=255)

    def validate(self, attrs):
        has_source_store = attrs.get("source_store_id") is not None
        has_source_hub = attrs.get("source_hub_id") is not None

        if has_source_store == has_source_hub:
            raise serializers.ValidationError(
                "Provide exactly one source: source_store_id or source_hub_id."
            )

        return attrs

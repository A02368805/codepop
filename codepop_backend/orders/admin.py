from django.contrib import admin

from .models import (
	HubInventoryBalance,
	InventoryItem,
	Region,
	RegionAssignment,
	RestockAlert,
	Store,
	StoreInventoryBalance,
	SupplyHub,
	SupplyTransfer,
)


admin.site.register(Region)
admin.site.register(Store)
admin.site.register(SupplyHub)
admin.site.register(RegionAssignment)
admin.site.register(InventoryItem)
admin.site.register(StoreInventoryBalance)
admin.site.register(HubInventoryBalance)
admin.site.register(RestockAlert)
admin.site.register(SupplyTransfer)

# Register your models here.

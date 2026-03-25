from django.urls import path

from .views import InventoryAdjustView, InventoryWorkspaceView

app_name = "inventory"

urlpatterns = [
    path("", InventoryWorkspaceView.as_view(), name="index"),
    path("adjust/<uuid:balance_id>/", InventoryAdjustView.as_view(), name="adjust"),
]

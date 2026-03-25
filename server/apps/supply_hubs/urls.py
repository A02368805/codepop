from django.urls import path

from .views import (
    SupplierOrderCancelView,
    SupplierOrderCreateView,
    SupplierOrderListView,
    SupplierOrderReceiveView,
    SupplyHubWorkspaceView,
    SupplyScheduleApproveView,
    SupplyScheduleListView,
    TransferApproveView,
    TransferCreateView,
    TransferDeliverView,
    TransferReceiveView,
    TransferReserveView,
    TransferShipView,
    TransferTableView,
)

app_name = "supply_hubs"

urlpatterns = [
    path("", SupplyHubWorkspaceView.as_view(), name="index"),
    path("transfers/create/", TransferCreateView.as_view(), name="create-transfer"),
    path("transfers/table/", TransferTableView.as_view(), name="transfer-table"),
    path(
        "transfers/<uuid:transfer_id>/approve/",
        TransferApproveView.as_view(),
        name="approve-transfer",
    ),
    path(
        "transfers/<uuid:transfer_id>/reserve/",
        TransferReserveView.as_view(),
        name="reserve-transfer",
    ),
    path(
        "transfers/<uuid:transfer_id>/ship/",
        TransferShipView.as_view(),
        name="ship-transfer",
    ),
    path(
        "transfers/<uuid:transfer_id>/deliver/",
        TransferDeliverView.as_view(),
        name="deliver-transfer",
    ),
    path(
        "transfers/<uuid:transfer_id>/receive/",
        TransferReceiveView.as_view(),
        name="receive-transfer",
    ),
    path("schedules/", SupplyScheduleListView.as_view(), name="schedule-list"),
    path(
        "schedules/<uuid:schedule_id>/approve/",
        SupplyScheduleApproveView.as_view(),
        name="approve-schedule",
    ),
    path(
        "supplier-orders/", SupplierOrderListView.as_view(), name="supplier-order-list"
    ),
    path(
        "supplier-orders/create/",
        SupplierOrderCreateView.as_view(),
        name="create-supplier-order",
    ),
    path(
        "supplier-orders/<uuid:replenishment_id>/receive/",
        SupplierOrderReceiveView.as_view(),
        name="receive-supplier-order",
    ),
    path(
        "supplier-orders/<uuid:replenishment_id>/cancel/",
        SupplierOrderCancelView.as_view(),
        name="cancel-supplier-order",
    ),
]

from django.contrib import admin
from django.urls import include, path

handler403 = "config.error_views.permission_denied"
handler404 = "config.error_views.page_not_found"
handler500 = "config.error_views.server_error"


urlpatterns = [
    path("", include("apps.users.urls")),
    path("admin/", admin.site.urls),
    path("stores/", include("apps.stores.urls")),
    path("orders/", include("apps.orders.urls")),
    path("support/", include("apps.support.urls")),
    path("payments/", include("apps.payments.urls")),
    path("inventory/", include("apps.inventory.urls")),
    path("supply-hubs/", include("apps.supply_hubs.urls")),
    path("maintenance/", include("apps.maintenance.urls")),
    path("notifications/", include("apps.notifications.urls")),
    path("imports/", include("apps.imports.urls")),
    path("sync/", include("apps.sync.urls")),
    path("analytics/", include("apps.analytics.urls")),
]

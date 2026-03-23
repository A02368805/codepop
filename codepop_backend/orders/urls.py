from django.urls import path
from .views import (
	LogisticsDashboardAPIView,
	LogisticsDashboardTemplateView,
	SupplyTransferCreateAPIView,
	SupplyTransferStatusAPIView,
)

app_name = 'orders'

urlpatterns = [
	path('logistics/dashboard/<int:region_id>/', LogisticsDashboardAPIView.as_view(), name='logistics-dashboard-api'),
	path('logistics/transfers/', SupplyTransferCreateAPIView.as_view(), name='logistics-transfer-create'),
	path(
		'logistics/transfers/<int:transfer_id>/<str:action>/',
		SupplyTransferStatusAPIView.as_view(),
		name='logistics-transfer-status',
	),
	path(
		'logistics/web/dashboard/<int:region_id>/',
		LogisticsDashboardTemplateView.as_view(),
		name='logistics-dashboard-web',
	),
]

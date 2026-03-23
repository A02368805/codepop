from django.contrib import messages
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q, F
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

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
from .serializers import (
	HubInventoryBalanceSerializer,
	RestockAlertSerializer,
	StoreInventoryBalanceSerializer,
	SupplyTransferCreateSerializer,
	SupplyTransferSerializer,
)


class LogisticsPermissionMixin:
	permission_classes = [IsAuthenticated]

	def get_assigned_regions(self, user):
		if user.is_superuser:
			return Region.objects.all()

		return Region.objects.filter(
			assignments__user=user,
			assignments__role="logistics_manager",
		).distinct()

	def ensure_region_access(self, user, region_id):
		allowed_regions = self.get_assigned_regions(user)
		if not allowed_regions.filter(id=region_id).exists():
			return None
		return allowed_regions.get(id=region_id)


def _create_or_resolve_alert(balance):
	open_alert = RestockAlert.objects.filter(
		store=balance.store,
		item=balance.item,
		status="open",
	).first()

	if balance.quantity <= balance.threshold:
		severity = "critical" if balance.quantity == 0 else "low"
		message = (
			f"{balance.item.name} at {balance.store.name} is low: "
			f"{balance.quantity} {balance.item.unit} remaining"
		)
		if open_alert:
			open_alert.severity = severity
			open_alert.message = message
			open_alert.save(update_fields=["severity", "message"])
			return

		RestockAlert.objects.create(
			store=balance.store,
			item=balance.item,
			severity=severity,
			status="open",
			message=message,
		)
		return

	if open_alert:
		open_alert.status = "resolved"
		open_alert.resolved_at = timezone.now()
		open_alert.save(update_fields=["status", "resolved_at"])


def _validate_and_create_transfer(actor, payload, permission_mixin):
	serializer = SupplyTransferCreateSerializer(data=payload)
	if not serializer.is_valid():
		error_payload = serializer.errors
		if isinstance(error_payload, dict):
			if "non_field_errors" in error_payload and error_payload["non_field_errors"]:
				return None, str(error_payload["non_field_errors"][0]), status.HTTP_400_BAD_REQUEST
			first_key = next(iter(error_payload), None)
			if first_key and error_payload[first_key]:
				error_msg = str(error_payload[first_key][0])
				return None, f"{first_key}: {error_msg}", status.HTTP_400_BAD_REQUEST
		return None, "Invalid transfer input.", status.HTTP_400_BAD_REQUEST
	data = serializer.validated_data

	destination_store = get_object_or_404(Store, id=data["destination_store_id"])
	destination_region_id = destination_store.region_id
	allowed_region = permission_mixin.ensure_region_access(actor, destination_region_id)
	if not allowed_region:
		return None, "Forbidden for destination region.", status.HTTP_403_FORBIDDEN

	source_store = None
	source_hub = None
	if data.get("source_store_id"):
		source_store = get_object_or_404(Store, id=data["source_store_id"])
		if source_store.region_id != destination_region_id:
			return None, "Cross-region transfers are not allowed.", status.HTTP_400_BAD_REQUEST

	if data.get("source_hub_id"):
		source_hub = get_object_or_404(SupplyHub, id=data["source_hub_id"])
		if source_hub.region_id != destination_region_id:
			return None, "Cross-region transfers are not allowed.", status.HTTP_400_BAD_REQUEST

	item = get_object_or_404(InventoryItem, id=data["item_id"])
	transfer = SupplyTransfer.objects.create(
		source_store=source_store,
		source_hub=source_hub,
		destination_store=destination_store,
		item=item,
		quantity=data["quantity"],
		requested_by=actor,
		note=data.get("note", ""),
	)

	return transfer, "Created", status.HTTP_201_CREATED


@transaction.atomic
def _apply_transfer_action(actor, transfer, action, permission_mixin):
	region = transfer.destination_store.region
	if not permission_mixin.ensure_region_access(actor, region.id):
		return "Forbidden for this region.", status.HTTP_403_FORBIDDEN

	if action == "approve":
		if transfer.status != "pending":
			return "Only pending transfers can be approved.", status.HTTP_400_BAD_REQUEST
		transfer.status = "approved"
		transfer.approved_by = actor
		transfer.approved_at = timezone.now()
		transfer.save(update_fields=["status", "approved_by", "approved_at"])
		return None, status.HTTP_200_OK

	if action == "reject":
		if transfer.status != "pending":
			return "Only pending transfers can be rejected.", status.HTTP_400_BAD_REQUEST
		transfer.status = "rejected"
		transfer.approved_by = actor
		transfer.approved_at = timezone.now()
		transfer.save(update_fields=["status", "approved_by", "approved_at"])
		return None, status.HTTP_200_OK

	if action == "complete":
		if transfer.status != "approved":
			return "Only approved transfers can be completed.", status.HTTP_400_BAD_REQUEST

		if transfer.source_store:
			source_balance = StoreInventoryBalance.objects.select_for_update().filter(
				store=transfer.source_store,
				item=transfer.item,
			).first()
			if not source_balance or source_balance.quantity < transfer.quantity:
				return "Insufficient source store inventory.", status.HTTP_400_BAD_REQUEST
			source_balance.quantity -= transfer.quantity
			source_balance.save(update_fields=["quantity", "updated_at"])
			_create_or_resolve_alert(source_balance)

		if transfer.source_hub:
			hub_balance = HubInventoryBalance.objects.select_for_update().filter(
				hub=transfer.source_hub,
				item=transfer.item,
			).first()
			if not hub_balance or hub_balance.quantity < transfer.quantity:
				return "Insufficient hub inventory.", status.HTTP_400_BAD_REQUEST
			hub_balance.quantity -= transfer.quantity
			hub_balance.save(update_fields=["quantity", "updated_at"])

		destination_balance, _ = StoreInventoryBalance.objects.select_for_update().get_or_create(
			store=transfer.destination_store,
			item=transfer.item,
			defaults={"quantity": 0, "threshold": 0},
		)
		destination_balance.quantity += transfer.quantity
		destination_balance.save(update_fields=["quantity", "updated_at"])
		_create_or_resolve_alert(destination_balance)

		transfer.status = "completed"
		transfer.completed_at = timezone.now()
		transfer.save(update_fields=["status", "completed_at"])
		return None, status.HTTP_200_OK

	return "Invalid action.", status.HTTP_400_BAD_REQUEST


def _effective_dashboard_user(request):
	if request.user.is_authenticated:
		return request.user

	return User.objects.filter(username="logistics_demo").first()


class LogisticsDashboardAPIView(LogisticsPermissionMixin, APIView):
	def get(self, request, region_id):
		region = self.ensure_region_access(request.user, region_id)
		if not region:
			return Response({"detail": "Forbidden for this region."}, status=status.HTTP_403_FORBIDDEN)

		store_balances = StoreInventoryBalance.objects.filter(store__region=region).select_related(
			"store", "item", "store__region"
		)
		hub_balances = HubInventoryBalance.objects.filter(hub__region=region).select_related(
			"hub", "item", "hub__region"
		)
		transfers = SupplyTransfer.objects.filter(
			Q(destination_store__region=region)
			| Q(source_store__region=region)
			| Q(source_hub__region=region)
		).select_related("source_store", "source_hub", "destination_store", "item")[:50]
		alerts = RestockAlert.objects.filter(store__region=region, status="open").select_related(
			"store", "item", "store__region"
		)

		return Response(
			{
				"region": {"id": region.id, "name": region.name, "code": region.code},
				"store_inventory": StoreInventoryBalanceSerializer(store_balances, many=True).data,
				"hub_inventory": HubInventoryBalanceSerializer(hub_balances, many=True).data,
				"pending_transfers": SupplyTransferSerializer(
					transfers.filter(status__in=["pending", "approved"]),
					many=True,
				).data,
				"restock_alerts": RestockAlertSerializer(alerts, many=True).data,
			}
		)


class SupplyTransferCreateAPIView(LogisticsPermissionMixin, APIView):
	def post(self, request):
		transfer, error_message, status_code = _validate_and_create_transfer(request.user, request.data, self)
		if error_message != "Created":
			return Response({"detail": error_message}, status=status_code)
		return Response(SupplyTransferSerializer(transfer).data, status=status.HTTP_201_CREATED)


class SupplyTransferStatusAPIView(LogisticsPermissionMixin, APIView):
	def post(self, request, transfer_id, action):
		transfer = get_object_or_404(
			SupplyTransfer.objects.select_for_update().select_related(
				"destination_store",
				"source_store",
				"source_hub",
				"item",
			),
			id=transfer_id,
		)

		error_message, status_code = _apply_transfer_action(request.user, transfer, action, self)
		if error_message:
			return Response({"detail": error_message}, status=status_code)
		return Response(SupplyTransferSerializer(transfer).data)


def _calculate_recommended_transfers(region):
	"""
	Suggest transfers to fill low-stock stores.
	For each store/item combo with low stock, find hubs or other stores that can supply it.
	"""
	recommendations = []
	
	# Get all low-stock items (< 50% of threshold)
	low_stock_balances = StoreInventoryBalance.objects.filter(
		store__region=region,
		quantity__lte=F('threshold') * 0.5
	).select_related('store', 'item')
	
	for balance in low_stock_balances:
		needed_qty = max(balance.threshold - balance.quantity, 10)  # at least 10 units or full threshold
		
		# Check hubs in same region
		hub_sources = HubInventoryBalance.objects.filter(
			hub__region=region,
			item=balance.item,
			quantity__gte=needed_qty
		).select_related('hub')
		
		# Check other stores in same region with surplus
		store_sources = StoreInventoryBalance.objects.filter(
			store__region=region,
			item=balance.item,
			quantity__gte=needed_qty * 1.5  # Need surplus
		).exclude(store=balance.store).select_related('store')
		
		for hub_source in hub_sources:
			recommendations.append({
				'destination_store': balance.store,
				'destination_store_id': balance.store.id,
				'item': balance.item,
				'item_id': balance.item.id,
				'suggested_qty': needed_qty,
				'source_type': 'hub',
				'source_name': hub_source.hub.name,
				'source_id': hub_source.hub.id,
				'available_qty': hub_source.quantity,
				'priority': 'high',
			})
		
		for store_source in store_sources:
			recommendations.append({
				'destination_store': balance.store,
				'destination_store_id': balance.store.id,
				'item': balance.item,
				'item_id': balance.item.id,
				'suggested_qty': needed_qty,
				'source_type': 'store',
				'source_name': store_source.store.name,
				'source_id': store_source.store.id,
				'available_qty': store_source.quantity,
				'priority': 'medium',
			})
	
	return recommendations[:10]  # Return top 10 recommendations


def _calculate_predicted_stockouts(region):
	"""
	Identify stores at critical risk of stockout.
	Based on current stock level vs threshold and alert history.
	"""
	predictions = []
	
	# Get all critical alerts (these flag stores near stockout)
	critical_alerts = RestockAlert.objects.filter(
		store__region=region,
		status='open',
		severity='critical'
	).select_related('store', 'item')
	
	for alert in critical_alerts:
		store_balance = StoreInventoryBalance.objects.filter(
			store=alert.store,
			item=alert.item
		).first()
		
		if store_balance and store_balance.quantity <= 1:
			# Estimate: at zero, store is critically out
			days_remaining = 0
		elif store_balance and store_balance.quantity > 0:
			# Conservative: assume 2-3 days usage at current burn rate
			days_remaining = max(1, min(store_balance.quantity, 3))
		else:
			continue
		
		predictions.append({
			'store': alert.store,
			'store_id': alert.store.id,
			'item': alert.item,
			'item_id': alert.item.id,
			'current_qty': store_balance.quantity if store_balance else 0,
			'days_remaining': days_remaining,
			'severity': 'critical' if days_remaining <= 1 else 'urgent',
			'message': f"{alert.item.name}: {days_remaining} days until stockout"
		})
	
	return predictions[:5]  # Top 5 at-risk items


def _identify_at_risk_items(store_balances):
	"""
	Mark inventory items that are below 30% of threshold as 'at-risk'.
	"""
	at_risk = []
	
	for balance in store_balances:
		if balance.threshold > 0:
			stock_ratio = (balance.quantity * 100) / balance.threshold
			if stock_ratio < 30:
				at_risk.append({
					'balance': balance,
					'stock_ratio': int(stock_ratio),
					'status': 'critical' if stock_ratio < 10 else 'warning'
				})
	
	return at_risk


class LogisticsDashboardTemplateView(LogisticsPermissionMixin, View):
	permission_classes = [AllowAny]

	def _build_context(self, region, actor):
		regions_qs = Region.objects.all().order_by("code")
		if actor and not actor.is_superuser:
			regions_qs = self.get_assigned_regions(actor).order_by("code")

		store_balances = StoreInventoryBalance.objects.filter(store__region=region).select_related(
			"store", "item"
		).order_by("store__name", "item__name")

		return {
			"region": region,
			"regions": regions_qs,
			"stores": Store.objects.filter(region=region).order_by("name"),
			"hubs": SupplyHub.objects.filter(region=region).order_by("name"),
			"items": InventoryItem.objects.all().order_by("name"),
			"store_balances": store_balances,
			"hub_balances": HubInventoryBalance.objects.filter(hub__region=region)
			.select_related("hub", "item")
			.order_by("hub__name", "item__name"),
			"pending_transfers": SupplyTransfer.objects.filter(
				Q(destination_store__region=region)
				| Q(source_store__region=region)
				| Q(source_hub__region=region),
				status__in=["pending", "approved"],
			)
			.select_related("source_store", "source_hub", "destination_store", "item")
			.order_by("-created_at")[:25],
			"alerts": RestockAlert.objects.filter(store__region=region, status="open")
			.select_related("store", "item")
			.order_by("-created_at"),
			"recommended_transfers": _calculate_recommended_transfers(region),
			"predicted_stockouts": _calculate_predicted_stockouts(region),
			"at_risk_items": _identify_at_risk_items(store_balances),
		}

	def get(self, request, region_id):
		actor = _effective_dashboard_user(request)
		region = get_object_or_404(Region, id=region_id)
		if actor and not actor.is_superuser and not self.get_assigned_regions(actor).filter(id=region_id).exists():
			return HttpResponseForbidden("You do not have access to this region.")

		context = self._build_context(region, actor)
		context["actor"] = actor
		return render(request, "orders/logistics_dashboard.html", context)

	@transaction.atomic
	def post(self, request, region_id):
		actor = _effective_dashboard_user(request)
		if not actor:
			messages.error(request, "No demo user found. Run seed_logistics_demo first.")
			return redirect("orders:logistics-dashboard-web", region_id=region_id)

		region = get_object_or_404(Region, id=region_id)
		if not actor.is_superuser and not self.get_assigned_regions(actor).filter(id=region_id).exists():
			messages.error(request, "You do not have access to this region.")
			return redirect("orders:logistics-dashboard-web", region_id=region_id)

		operation = request.POST.get("operation")
		if operation == "create_transfer":
			payload = {
				"destination_store_id": request.POST.get("destination_store_id"),
				"item_id": request.POST.get("item_id"),
				"quantity": request.POST.get("quantity"),
				"note": request.POST.get("note", ""),
			}
			# Only include source fields if they have values
			source_hub = request.POST.get("source_hub_id")
			source_store = request.POST.get("source_store_id")
			if source_hub:
				payload["source_hub_id"] = source_hub
			if source_store:
				payload["source_store_id"] = source_store
			transfer, error_message, status_code = _validate_and_create_transfer(actor, payload, self)
			if status_code == status.HTTP_201_CREATED:
				messages.success(request, f"Transfer #{transfer.id} created.")
			else:
				messages.error(request, error_message)

		if operation == "transfer_action":
			transfer_id = request.POST.get("transfer_id")
			action = request.POST.get("transfer_action")
			transfer = get_object_or_404(
				SupplyTransfer.objects.select_related(
					"destination_store",
					"source_store",
					"source_hub",
					"item",
				),
				id=transfer_id,
			)
			error_message, status_code = _apply_transfer_action(actor, transfer, action, self)
			if status_code == status.HTTP_200_OK:
				label = {"approve": "approved", "reject": "rejected", "complete": "completed"}.get(action, action)
				messages.success(request, f"Transfer #{transfer.id} {label} successfully.")
			else:
				messages.error(request, error_message)

		target_region = request.POST.get("target_region")
		if target_region:
			return redirect("orders:logistics-dashboard-web", region_id=target_region)

		return redirect("orders:logistics-dashboard-web", region_id=region_id)

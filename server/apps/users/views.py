from datetime import timedelta

from apps.analytics.recommendations import recommend_drinks_for_user
from apps.analytics.selectors import build_dashboard_payload
from apps.imports.models import ImportJob
from apps.inventory.models import (
    LocalSupplier,
    RestockAlert,
    StoreInventoryBalance,
    SupplierReplenishment,
    SupplySchedule,
    SupplyUsageRecord,
)
from apps.inventory.selectors import (
    build_transfer_recommendations,
    summarize_store_inventory_health,
)
from apps.maintenance.models import Machine, RepairAssignment
from apps.maintenance.selectors import build_route_groups
from apps.notifications.models import Notification
from apps.orders.catalog import (
    ADD_IN_GROUPS,
    ADD_IN_OPTIONS,
    ADVENTUROUSNESS_PREFERENCE_CHOICES,
    DIETARY_PREFERENCE_OPTIONS,
    ICE_CREAM_GROUPS,
    ICE_CREAM_OPTIONS,
    SODA_GROUPS,
    SODA_OPTIONS,
    SWEETNESS_PREFERENCE_CHOICES,
    SYRUP_GROUPS,
    SYRUP_OPTIONS,
    get_menu_items,
    grouped_options,
)
from apps.orders.models import Order
from apps.orders.selectors import staff_order_queue
from apps.payments.models import RevenueLedgerEntry
from apps.stores.models import Region, Store
from apps.stores.selectors import (
    regions_visible_to_user,
    scoped_region_store_options,
    stores_visible_to_user,
)
from apps.supply_hubs.models import HubInventoryBalance, SupplyHub, SupplyTransfer
from apps.sync.models import (
    AuditLog,
    SyncConflictLog,
    SyncOutboxEvent,
    SyncProjectionState,
)
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.db.models import Count, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.templatetags.static import static
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import FormView, TemplateView, View

from .forms import (
    EmailAuthenticationForm,
    PreferenceProfileForm,
    RegistrationForm,
    ScopedUserUpdateForm,
)
from .models import User
from .permissions import (
    RoleRequiredMixin,
    user_can_use_customer_ordering,
    user_has_global_access,
)
from .selectors import get_dashboard_template, get_role_cards
from .services import get_post_login_url, save_preference_profile, update_scoped_user

HOME_BASE_FAMILIES = [
    {
        "key": "coke",
        "label": "Coke",
        "slugs": {"coke", "diet-coke", "coke-zero"},
        "description": "Classic cola favorites and zero-sugar picks.",
    },
    {
        "key": "pepsi",
        "label": "Pepsi",
        "slugs": {"pepsi", "diet-pepsi"},
        "description": "Smooth Pepsi builds with bright and creamy options.",
    },
    {
        "key": "mtn-dew",
        "label": "Mtn Dew",
        "slugs": {"mountain-dew", "diet-mountain-dew"},
        "description": "Bolder citrus profiles with extra flavor energy.",
    },
    {
        "key": "dr-pepper",
        "label": "Dr Pepper",
        "slugs": {"dr-pepper", "diet-dr-pepper"},
        "description": "Spiced cola-style combinations with layered sweetness.",
    },
    {
        "key": "sprite",
        "label": "Sprite",
        "slugs": {"sprite", "sprite-zero", "lemon-lime"},
        "description": "Crisp citrus and clean soda-shop refreshers.",
    },
    {
        "key": "root-beer",
        "label": "Root Beer",
        "slugs": {"root-beer"},
        "description": "Rich root-beer recipes built for smooth finishes.",
    },
]

HOME_BASE_IMAGE_ASSETS = {
    "coke": "images/drinks/hero-coke.svg",
    "diet-coke": "images/drinks/hero-coke.svg",
    "coke-zero": "images/drinks/hero-coke.svg",
    "pepsi": "images/drinks/hero-pepsi.svg",
    "diet-pepsi": "images/drinks/hero-pepsi.svg",
    "mountain-dew": "images/drinks/hero-mtn-dew.svg",
    "diet-mountain-dew": "images/drinks/hero-mtn-dew.svg",
    "dr-pepper": "images/drinks/hero-dr-pepper.svg",
    "diet-dr-pepper": "images/drinks/hero-dr-pepper.svg",
    "sprite": "images/drinks/hero-sprite.svg",
    "sprite-zero": "images/drinks/hero-sprite.svg",
    "lemon-lime": "images/drinks/hero-sprite.svg",
    "root-beer": "images/drinks/hero-root-beer.svg",
    "orange-soda": "images/drinks/hero-orange-soda.svg",
    "club-soda": "images/drinks/hero-club-soda.svg",
    "cream-soda": "images/drinks/hero-cream-soda.svg",
}

HOME_FEATURED_SLUGS = [
    "orange-creamsicle",
    "vanilla-sunset",
    "sprite-garden-fizz",
    "root-beer-cocoa-float",
    "dew-lime-launch",
]


def _parse_date(value):
    if not value:
        return None
    try:
        return timezone.datetime.fromisoformat(value).date()
    except ValueError:
        return None


def _resolve_window(window, date_from, date_to):
    today = timezone.now().date()
    if window == "custom" and date_from and date_to:
        return date_from, date_to
    if window == "week":
        return today - timedelta(days=6), today
    return today - timedelta(days=29), today


def _build_preference_cards(*, name, groups, selected_values):
    selected_values = set(selected_values or [])
    payload = []
    for group in groups:
        payload.append(
            {
                "label": group["label"],
                "description": group.get("description", ""),
                "items": [
                    {
                        "id": f"id_{name}_{item['value']}",
                        "name": name,
                        "value": item["value"],
                        "label": item["label"],
                        "description": item.get("description", ""),
                        "checked": item["value"] in selected_values,
                    }
                    for item in group["items"]
                ],
            }
        )
    return payload


def _form_list_value(form, field_name):
    if form.is_bound and hasattr(form.data, "getlist"):
        return form.data.getlist(field_name)
    value = form.initial.get(field_name, form.fields[field_name].initial or [])
    return list(value or [])


def _form_scalar_value(form, field_name):
    if form.is_bound:
        return form.data.get(field_name, "")
    return form.initial.get(field_name, form.fields[field_name].initial or "")


def _home_base_category(base_slug):
    for family in HOME_BASE_FAMILIES:
        if base_slug in family["slugs"]:
            return family["key"], family["label"], family.get("description", "")

    fallback = SODA_OPTIONS.get(base_slug, {})
    return (
        base_slug,
        fallback.get("label", base_slug.replace("-", " ").title()),
        fallback.get("description", ""),
    )


class HomePageView(TemplateView):
    template_name = "home.html"

    def _default_ordering_store(self):
        user = self.request.user
        if (
            getattr(user, "is_authenticated", False)
            and user.role == User.Role.ACCOUNT_USER
            and user.preferred_store
            and user.preferred_store.is_active
        ):
            return user.preferred_store
        return Store.objects.filter(is_active=True).order_by("store_code").first()

    def _build_customer_menu_sections(self, *, store):
        menu_items = get_menu_items()
        cards = []
        categories = {}
        float_cards = []

        for item in menu_items:
            base_slug = item.get("default_soda", "")
            base_option = SODA_OPTIONS.get(base_slug, {})
            category_key, category_label, category_description = _home_base_category(
                base_slug
            )
            tags = list(item.get("tags", []))
            has_float_profile = bool(item.get("default_ice_cream")) or any(
                str(tag).lower() == "float" for tag in tags
            )
            base_image_asset = HOME_BASE_IMAGE_ASSETS.get(
                base_slug, "images/drinks/hero-float.svg"
            )
            if has_float_profile and item.get("default_ice_cream"):
                base_image_asset = "images/drinks/hero-float.svg"
            card = {
                "slug": item["slug"],
                "name": item["name"],
                "description": item.get("description", ""),
                "base_slug": base_slug,
                "base_label": base_option.get(
                    "label", base_slug.replace("-", " ").title()
                ),
                "category_key": category_key,
                "category_label": category_label,
                "tags": tags[:3],
                "badge": item.get("home_badge", ""),
                "starting_price": item["base_prices"].get("small", ""),
                "image_url": static(base_image_asset),
                "image_alt": f"{item['name']} custom soda in an iced cup",
                "customize_url": (
                    reverse("orders:customize", args=[store.store_code, item["slug"]])
                    if store
                    else reverse("stores:index")
                ),
            }
            cards.append(card)
            categories.setdefault(
                category_key,
                {
                    "key": category_key,
                    "label": category_label,
                    "description": category_description,
                    "cards": [],
                },
            )["cards"].append(card)
            if has_float_profile:
                float_cards.append(card)

        sections = []

        for family in HOME_BASE_FAMILIES:
            family_section = categories.get(family["key"])
            if family_section:
                family_section["description"] = family.get(
                    "description", family_section.get("description", "")
                )
                family_section["count"] = len(family_section["cards"])
                family_section["anchor_id"] = f"home-section-{family_section['key']}"
                sections.append(family_section)

        family_keys = {family["key"] for family in HOME_BASE_FAMILIES}
        extra_sections = [
            section
            for key, section in categories.items()
            if key not in family_keys and section["cards"]
        ]
        for section in sorted(extra_sections, key=lambda value: value["label"]):
            section["count"] = len(section["cards"])
            section["anchor_id"] = f"home-section-{section['key']}"
            sections.append(section)

        if float_cards:
            sections.append(
                {
                    "key": "floats",
                    "label": "Floats",
                    "description": "Creamier float builds with ice-cream-forward profiles.",
                    "cards": float_cards,
                    "count": len(float_cards),
                    "anchor_id": "home-section-floats",
                }
            )

        cards_by_slug = {card["slug"]: card for card in cards}
        featured_cards = [
            cards_by_slug[slug] for slug in HOME_FEATURED_SLUGS if slug in cards_by_slug
        ]
        for card in cards:
            if len(featured_cards) >= 5:
                break
            if card not in featured_cards:
                featured_cards.append(card)
        hero_slides = [
            {
                "id": f"hero-slide-{index}",
                "name": card["name"],
                "description": card["description"],
                "badge": card["badge"] or "Featured",
                "image_url": card["image_url"],
                "image_alt": card["image_alt"],
                "customize_url": card["customize_url"],
                "base_label": card["base_label"],
            }
            for index, card in enumerate(featured_cards, start=1)
        ]

        return cards, sections, hero_slides

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        can_start_order = user_can_use_customer_ordering(self.request.user)
        context["can_start_order"] = can_start_order
        context["role_cards"] = get_role_cards()
        context["platform_principles"] = [
            "Customer ordering and internal operations in one server-rendered product",
            "Strict role scoping with permissions enforced on the server",
            "Regional logistics, maintenance, payments, and analytics in one workflow shell",
            "Demo-friendly UX without losing operational realism",
        ]
        if can_start_order:
            store = self._default_ordering_store()
            cards, sections, hero_slides = self._build_customer_menu_sections(
                store=store
            )
            context["default_ordering_store"] = store
            context["home_menu_cards"] = cards
            context["home_menu_sections"] = sections
            context["home_hero_slides"] = hero_slides
            context["home_browse_url"] = (
                reverse("orders:menu", args=[store.store_code])
                if store
                else reverse("stores:index")
            )
            context["home_menu_nav"] = [
                {
                    "key": section["key"],
                    "label": section["label"],
                    "count": section["count"],
                    "anchor_id": section["anchor_id"],
                }
                for section in sections
            ]
        return context


class CodePopLoginView(LoginView):
    template_name = "registration/login.html"
    authentication_form = EmailAuthenticationForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return get_post_login_url(self.request.user)


class CodePopLogoutView(LogoutView):
    pass


class RegisterView(FormView):
    template_name = "registration/register.html"
    form_class = RegistrationForm

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        messages.success(
            self.request,
            "Your account is ready. Start with your store and preferences.",
        )
        return redirect(get_post_login_url(user))


class RoleAwareDashboardRedirectView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        return redirect(get_post_login_url(request.user))


class BaseDashboardView(RoleRequiredMixin, TemplateView):
    required_role = None

    def get_template_names(self):
        return [get_dashboard_template(self.required_role)]

    @property
    def allowed_roles(self):
        return (self.required_role,)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dashboard"] = build_dashboard_payload(
            user=self.request.user, role=self.required_role
        )
        return context


class CustomerDashboardView(BaseDashboardView):
    required_role = User.Role.ACCOUNT_USER

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["recent_orders"] = self.request.user.orders.select_related(
            "store"
        ).order_by("-created_at")[:5]
        context["favorite_drinks"] = self.request.user.favorite_drinks.order_by("name")[
            :4
        ]
        context["taste_preferences"] = self.request.user.taste_preferences.order_by(
            "ingredient_name"
        )
        context["recommended_drinks"] = recommend_drinks_for_user(
            self.request.user, limit=3
        )
        context["notifications"] = Notification.objects.filter(
            user=self.request.user, is_read=False
        )[:4]
        return context


class ManagerDashboardView(BaseDashboardView):
    required_role = User.Role.MANAGER

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        stores = stores_visible_to_user(self.request.user)
        managed_store = stores.first()
        revenue_summary = RevenueLedgerEntry.objects.filter(store__in=stores).aggregate(
            gross=Sum("gross_amount"),
            net=Sum("net_amount"),
        )
        context["queue_preview"] = staff_order_queue(self.request.user)[:8]
        context["managed_store"] = managed_store
        context["low_stock_alerts"] = RestockAlert.objects.filter(
            store__in=stores,
            status=RestockAlert.Status.OPEN,
        ).select_related("store", "inventory_item")[:8]
        context["inventory_health_rows"] = summarize_store_inventory_health(
            visible_stores=stores
        )[:4]
        context["machine_summary"] = (
            Machine.objects.filter(store__in=stores)
            .values("current_status")
            .annotate(count=Count("id"))
        )
        context["gross_revenue"] = revenue_summary["gross"] or 0
        context["net_revenue"] = revenue_summary["net"] or 0
        context["notifications"] = Notification.objects.filter(
            user=self.request.user,
            is_read=False,
        ).order_by("-created_at")[:4]
        return context


class AdminDashboardView(BaseDashboardView):
    required_role = User.Role.ADMIN

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        managed_store = stores_visible_to_user(self.request.user).first()
        scoped_users = _scoped_users_for_admin(self.request.user)
        visible_stores = stores_visible_to_user(self.request.user)
        context["managed_store"] = managed_store
        context["scoped_users"] = scoped_users[:10]
        context["locked_count"] = scoped_users.filter(status=User.Status.LOCKED).count()
        context["disabled_count"] = scoped_users.filter(
            status=User.Status.DISABLED
        ).count()
        context["pending_count"] = scoped_users.filter(
            status=User.Status.PENDING
        ).count()
        context["role_breakdown"] = [
            {
                "label": User.Role(row["role"]).label,
                "count": row["count"],
            }
            for row in scoped_users.values("role")
            .annotate(count=Count("id"))
            .order_by("role")
        ]
        context["recent_audit_logs"] = AuditLog.objects.filter(
            store__in=visible_stores
        ).select_related("actor", "store", "region")[:8]
        context["recent_notifications"] = Notification.objects.filter(
            user=self.request.user,
            is_read=False,
        ).order_by("-created_at")[:4]
        context["machine_issue_count"] = Machine.objects.filter(
            store__in=visible_stores,
            current_status__in=[
                Machine.Status.WARNING,
                Machine.Status.ERROR,
                Machine.Status.OUT_OF_ORDER,
            ],
        ).count()
        return context


class LogisticsDashboardView(BaseDashboardView):
    required_role = User.Role.LOGISTICS_MANAGER

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        scope = scoped_region_store_options(
            self.request.user,
            region_id=self.request.GET.get("region", "").strip(),
            store_id=self.request.GET.get("store", "").strip(),
        )
        date_from = _parse_date(self.request.GET.get("date_from", "").strip())
        date_to = _parse_date(self.request.GET.get("date_to", "").strip())
        window = self.request.GET.get("window", "month").strip() or "month"
        date_from, date_to = _resolve_window(window, date_from, date_to)

        visible_stores = scope["active_store_scope"]
        scoped_regions = (
            scope["region_options"].filter(pk=scope["selected_region"].pk)
            if scope["selected_region"]
            else scope["region_options"]
        )
        pending_transfers = SupplyTransfer.objects.filter(
            destination_store__in=visible_stores,
            status__in=[
                SupplyTransfer.Status.REQUESTED,
                SupplyTransfer.Status.APPROVED,
                SupplyTransfer.Status.RESERVED,
            ],
        ).select_related(
            "destination_store",
            "source_store",
            "source_hub",
        )
        if date_from:
            pending_transfers = pending_transfers.filter(
                requested_at__date__gte=date_from
            )
        if date_to:
            pending_transfers = pending_transfers.filter(
                requested_at__date__lte=date_to
            )

        low_stock_alerts = RestockAlert.objects.filter(
            store__in=visible_stores,
            status=RestockAlert.Status.OPEN,
        ).select_related("store", "inventory_item")
        usage_rows = (
            SupplyUsageRecord.objects.filter(
                store__in=visible_stores,
                usage_date__gte=date_from,
                usage_date__lte=date_to,
            )
            .values("store__name")
            .annotate(total_used=Sum("quantity_used"))
            .order_by("-total_used", "store__name")[:8]
        )
        inventory_category_rows = (
            StoreInventoryBalance.objects.filter(store__in=visible_stores)
            .values("inventory_item__category")
            .annotate(
                total_on_hand=Sum("on_hand_quantity"),
                tracked_items=Count("inventory_item", distinct=True),
            )
            .order_by("-total_on_hand")
        )
        supplier_orders = SupplierReplenishment.objects.filter(
            store__in=visible_stores,
            status=SupplierReplenishment.Status.ORDERED,
        ).select_related("supplier", "store", "inventory_item")

        context.update(
            {
                "visible_regions": scope["region_options"],
                "hubs": SupplyHub.objects.filter(region__in=scoped_regions).order_by(
                    "hub_code"
                ),
                "hub_balances": HubInventoryBalance.objects.filter(
                    hub__region__in=scoped_regions
                )
                .select_related("hub", "inventory_item")
                .order_by("hub__name", "inventory_item__name")[:12],
                "pending_transfers": pending_transfers.order_by("-requested_at")[:8],
                "low_stock_alerts": low_stock_alerts.order_by("-created_at")[:8],
                "critical_alert_count": low_stock_alerts.filter(
                    severity=RestockAlert.Severity.CRITICAL
                ).count(),
                "recent_imports": ImportJob.objects.filter(
                    import_type=ImportJob.ImportType.SUPPLY_USAGE
                )
                .select_related("uploaded_by")
                .order_by("-created_at")[:8],
                "draft_schedules": SupplySchedule.objects.filter(
                    store__in=visible_stores,
                    created_by_ai=True,
                    status=SupplySchedule.Status.DRAFT,
                )
                .select_related("store", "inventory_item")
                .order_by("-created_at")[:8],
                "transfer_recommendations": build_transfer_recommendations(
                    visible_stores=visible_stores,
                    limit=6,
                ),
                "inventory_health_rows": summarize_store_inventory_health(
                    visible_stores=visible_stores
                )[:8],
                "usage_rows": usage_rows,
                "supplier_orders": supplier_orders.order_by("-ordered_at")[:8],
                "inventory_category_rows": inventory_category_rows[:6],
                "suppliers": LocalSupplier.objects.filter(
                    service_region__in=scoped_regions
                ).order_by("name")[:8],
                "window": window,
                "date_from": date_from.isoformat() if date_from else "",
                "date_to": date_to.isoformat() if date_to else "",
                "region_options": scope["region_options"],
                "store_options": scope["store_options"],
                "selected_region": scope["selected_region"],
                "selected_store": scope["selected_store"],
            }
        )
        return context


class RepairDashboardView(BaseDashboardView):
    required_role = User.Role.REPAIR_STAFF

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        visible_stores = stores_visible_to_user(self.request.user)
        context["urgent_machines"] = Machine.objects.filter(
            store__in=visible_stores,
            current_status__in=[
                Machine.Status.WARNING,
                Machine.Status.ERROR,
                Machine.Status.OUT_OF_ORDER,
                Machine.Status.SCHEDULE_SERVICE,
            ],
        ).select_related("store", "machine_type")[:10]
        context["assignments"] = (
            RepairAssignment.objects.filter(assigned_to=self.request.user)
            .select_related("machine", "store")
            .order_by("scheduled_for", "-priority_score")[:10]
        )
        context["route_groups"] = build_route_groups(context["assignments"])[:4]
        context["recent_imports"] = (
            ImportJob.objects.filter(import_type=ImportJob.ImportType.REPAIR_STATUS)
            .select_related("uploaded_by")
            .order_by("-created_at")[:8]
        )
        context["notifications"] = Notification.objects.filter(
            user=self.request.user,
            is_read=False,
        ).order_by("-created_at")[:4]
        return context


class SuperAdminDashboardView(BaseDashboardView):
    required_role = User.Role.SUPER_ADMIN

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["region_rows"] = Region.objects.annotate(
            store_count=Count("stores"),
            hub_count=Count("supply_hubs"),
        ).order_by("code")
        context["recent_audit_logs"] = AuditLog.objects.select_related(
            "actor", "store", "region"
        )[:12]
        context["account_summary"] = {
            "customers": User.objects.filter(role=User.Role.ACCOUNT_USER).count(),
            "staff": User.objects.exclude(role=User.Role.ACCOUNT_USER).count(),
            "stores": stores_visible_to_user(self.request.user).count(),
        }
        context["sync_summary"] = {
            "pending": SyncOutboxEvent.objects.filter(
                status=SyncOutboxEvent.Status.PENDING
            ).count(),
            "failed": SyncOutboxEvent.objects.filter(
                status=SyncOutboxEvent.Status.FAILED
            ).count(),
            "conflicts": SyncConflictLog.objects.filter(
                resolution_status=SyncConflictLog.ResolutionStatus.OPEN
            ).count(),
            "projections": SyncProjectionState.objects.count(),
        }
        context["pending_import_count"] = ImportJob.objects.filter(
            status=ImportJob.Status.PENDING
        ).count()
        context["machine_issue_count"] = Machine.objects.filter(
            current_status__in=[
                Machine.Status.WARNING,
                Machine.Status.ERROR,
                Machine.Status.OUT_OF_ORDER,
                Machine.Status.SCHEDULE_SERVICE,
            ]
        ).count()
        context["region_operations"] = Region.objects.annotate(
            transfer_count=Count("stores__inbound_transfers", distinct=True),
            machine_issue_count=Count(
                "stores__machines",
                filter=Q(
                    stores__machines__current_status__in=[
                        Machine.Status.WARNING,
                        Machine.Status.ERROR,
                        Machine.Status.OUT_OF_ORDER,
                        Machine.Status.SCHEDULE_SERVICE,
                    ]
                ),
                distinct=True,
            ),
        ).order_by("code")
        return context


class PreferenceView(RoleRequiredMixin, LoginRequiredMixin, FormView):
    template_name = "customer/preferences.html"
    form_class = PreferenceProfileForm
    allowed_roles = (User.Role.ACCOUNT_USER,)

    def get_initial(self):
        preferences = self.request.user.taste_preferences
        return {
            "favorite_sodas": list(
                preferences.filter(
                    preference_type=self.request.user.taste_preferences.model.PreferenceType.FAVORITE_SODA
                ).values_list("ingredient_name", flat=True)
            ),
            "favorite_syrups": list(
                preferences.filter(
                    preference_type=self.request.user.taste_preferences.model.PreferenceType.FAVORITE_SYRUP
                ).values_list("ingredient_name", flat=True)
            ),
            "favorite_add_ins": list(
                preferences.filter(
                    preference_type=self.request.user.taste_preferences.model.PreferenceType.FAVORITE_ADD_IN
                ).values_list("ingredient_name", flat=True)
            ),
            "favorite_ice_creams": list(
                preferences.filter(
                    preference_type=self.request.user.taste_preferences.model.PreferenceType.FAVORITE_ICE_CREAM
                ).values_list("ingredient_name", flat=True)
            ),
            "disliked_ingredients": list(
                preferences.filter(
                    preference_type=self.request.user.taste_preferences.model.PreferenceType.DISLIKE
                ).values_list("ingredient_name", flat=True)
            ),
            "dietary_preferences": list(
                preferences.filter(
                    preference_type=self.request.user.taste_preferences.model.PreferenceType.DIETARY
                ).values_list("ingredient_name", flat=True)
            ),
            "sweetness_preference": self.request.user.sweetness_preference,
            "adventurousness_preference": self.request.user.adventurousness_preference,
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = kwargs.get("form") or context.get("form") or self.get_form()
        context.update(
            {
                "form": form,
                "favorite_soda_cards": _build_preference_cards(
                    name="favorite_sodas",
                    groups=grouped_options(SODA_OPTIONS, SODA_GROUPS),
                    selected_values=_form_list_value(form, "favorite_sodas"),
                ),
                "favorite_syrup_cards": _build_preference_cards(
                    name="favorite_syrups",
                    groups=grouped_options(SYRUP_OPTIONS, SYRUP_GROUPS),
                    selected_values=_form_list_value(form, "favorite_syrups"),
                ),
                "favorite_add_in_cards": _build_preference_cards(
                    name="favorite_add_ins",
                    groups=grouped_options(ADD_IN_OPTIONS, ADD_IN_GROUPS),
                    selected_values=_form_list_value(form, "favorite_add_ins"),
                ),
                "favorite_ice_cream_cards": _build_preference_cards(
                    name="favorite_ice_creams",
                    groups=grouped_options(ICE_CREAM_OPTIONS, ICE_CREAM_GROUPS),
                    selected_values=_form_list_value(form, "favorite_ice_creams"),
                ),
                "disliked_ingredient_cards": _build_preference_cards(
                    name="disliked_ingredients",
                    groups=[
                        {
                            "label": "Sodas",
                            "description": "Bases FloatStack should steer away from.",
                            "items": [
                                {"value": key, **value}
                                for key, value in SODA_OPTIONS.items()
                            ],
                        },
                        {
                            "label": "Syrups",
                            "description": "Flavor shots to avoid.",
                            "items": [
                                {"value": key, **value}
                                for key, value in SYRUP_OPTIONS.items()
                            ],
                        },
                        {
                            "label": "Add-Ins + Ice Cream",
                            "description": "Finishing touches to keep out of AI suggestions.",
                            "items": [
                                {"value": key, **value}
                                for key, value in {
                                    **ADD_IN_OPTIONS,
                                    **ICE_CREAM_OPTIONS,
                                }.items()
                            ],
                        },
                    ],
                    selected_values=_form_list_value(form, "disliked_ingredients"),
                ),
                "dietary_cards": [
                    {
                        "id": f"id_dietary_preferences_{value}",
                        "name": "dietary_preferences",
                        "value": value,
                        "label": label,
                        "checked": value
                        in set(_form_list_value(form, "dietary_preferences")),
                    }
                    for value, label in DIETARY_PREFERENCE_OPTIONS
                ],
                "sweetness_options": [
                    {
                        "value": value,
                        "label": label,
                        "checked": value
                        == _form_scalar_value(form, "sweetness_preference"),
                    }
                    for value, label in SWEETNESS_PREFERENCE_CHOICES
                ],
                "adventurousness_options": [
                    {
                        "value": value,
                        "label": label,
                        "checked": value
                        == _form_scalar_value(form, "adventurousness_preference"),
                    }
                    for value, label in ADVENTUROUSNESS_PREFERENCE_CHOICES
                ],
                "saved_profile_count": self.request.user.taste_preferences.count(),
            }
        )
        return context

    def form_valid(self, form):
        save_preference_profile(
            user=self.request.user,
            favorite_sodas=form.cleaned_data["favorite_sodas"],
            favorite_syrups=form.cleaned_data["favorite_syrups"],
            favorite_add_ins=form.cleaned_data["favorite_add_ins"],
            favorite_ice_creams=form.cleaned_data["favorite_ice_creams"],
            disliked_ingredients=form.cleaned_data["disliked_ingredients"],
            dietary_preferences=form.cleaned_data["dietary_preferences"],
            sweetness_preference=form.cleaned_data["sweetness_preference"],
            adventurousness_preference=form.cleaned_data["adventurousness_preference"],
        )
        messages.success(self.request, "Your taste profile was updated.")
        return redirect("account-preferences")


def _scoped_users_for_admin(user):
    if user_has_global_access(user):
        return User.objects.order_by("email")
    managed_store = stores_visible_to_user(user).first()
    if not managed_store:
        return User.objects.none()
    return (
        (
            User.objects.filter(preferred_store=managed_store)
            | User.objects.filter(store_assignments__store=managed_store)
        )
        .distinct()
        .order_by("email")
    )


class AdminUserManagementView(RoleRequiredMixin, LoginRequiredMixin, TemplateView):
    template_name = "admin/users.html"
    allowed_roles = (User.Role.ADMIN, User.Role.SUPER_ADMIN)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["managed_store"] = (
            None
            if user_has_global_access(self.request.user)
            else stores_visible_to_user(self.request.user).first()
        )
        context["scoped_users"] = _scoped_users_for_admin(self.request.user)
        context["user_form"] = ScopedUserUpdateForm()
        return context


class AdminUserUpdateView(RoleRequiredMixin, LoginRequiredMixin, View):
    allowed_roles = (User.Role.ADMIN, User.Role.SUPER_ADMIN)

    def post(self, request, *args, **kwargs):
        target_user = get_object_or_404(User, pk=kwargs["user_id"])
        form = ScopedUserUpdateForm(request.POST)
        if form.is_valid():
            update_scoped_user(
                actor=request.user,
                target_user=target_user,
                role=form.cleaned_data["role"],
                status=form.cleaned_data["status"],
            )
            messages.success(request, f"{target_user.email} was updated.")
        else:
            messages.error(request, "Could not update that account.")
        return redirect("admin-users")


@method_decorator(csrf_exempt, name="dispatch")
class FederatedValidateView(View):
    """
    Machine-to-machine endpoint for cross-store user authentication.

    Other stores POST here when a user isn't found locally, to validate
    credentials and get basic user data. Uses X-Sync-Token header auth
    (same pattern as SyncIngestView).

    Only validates ACCOUNT_USER role — staff roles are store-local.
    """

    def post(self, request, *args, **kwargs):
        from django.conf import settings
        from django.contrib.auth import authenticate
        import json

        # Authenticate the requesting peer store
        token = request.headers.get("X-Sync-Token", "")
        if not token or token != settings.SYNC_API_SECRET:
            return JsonResponse({"error": "unauthorized"}, status=401)

        origin_node_id = request.headers.get("X-Origin-Node", "")
        if not origin_node_id:
            return JsonResponse({"error": "missing origin"}, status=400)

        # Parse request body
        try:
            data = json.loads(request.body)
            email = data.get("email", "")
            password = data.get("password", "")
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"error": "invalid json"}, status=400)

        # Authenticate the user locally
        user = authenticate(request, username=email, password=password)

        # Reject if user not found or not an account_user
        if not user or user.role != User.Role.ACCOUNT_USER:
            # Return 200 "valid=false" instead of 401/403 to avoid leaking user existence
            return JsonResponse({"valid": False}, status=200)

        # Valid account user — return their data
        return JsonResponse(
            {
                "valid": True,
                "user": {
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "role": user.role,
                    "sweetness_preference": user.sweetness_preference or "",
                    "adventurousness_preference": user.adventurousness_preference or "",
                },
            },
            status=200,
        )

import re
from datetime import date
from decimal import Decimal
from urllib.parse import urlencode

from apps.analytics.recommendations import recommend_drinks_for_user
from apps.payments.gateway import PaymentMode, get_payment_mode
from apps.payments.services import (
    PaymentGatewayError,
    initialize_order_checkout,
    record_refund,
)
from apps.stores.models import Store
from apps.stores.selectors import scoped_region_store_options
from apps.users.models import User
from apps.users.permissions import (
    CustomerOrderingRequiredMixin,
    RoleRequiredMixin,
    user_can_use_customer_ordering,
)
from apps.users.services import remove_favorite_drink, save_favorite_drink
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import FormView, TemplateView

from .assistant import build_drink_builder_assistance, build_menu_ai_assistance
from .cart import (
    add_cart_item,
    build_cart_pricing,
    cart_item_count,
    clear_cart,
    get_cart,
    remove_cart_item,
    update_cart_item,
)
from .catalog import (
    ADD_IN_GROUPS,
    ADD_IN_OPTIONS,
    ICE_CREAM_GROUPS,
    ICE_CREAM_OPTIONS,
    SIZE_LABELS,
    SODA_GROUPS,
    SODA_OPTIONS,
    SYRUP_GROUPS,
    SYRUP_OPTIONS,
    build_cart_item,
    get_menu_item,
    get_menu_items,
    grouped_options,
)
from .forms import (
    CartQuantityForm,
    CheckoutForm,
    DrinkCustomizationForm,
    GuestLookupForm,
    MenuAiPromptForm,
)
from .models import Order
from .personalization import recommend_builder_configuration
from .selectors import (
    account_order_history,
    authorize_guest_order_access,
    staff_order_queue,
    user_can_transition_order,
    user_can_view_order,
)
from .services import create_order, get_refund_eligibility, transition_order_status

PICKUP_COMBO_PATTERN = re.compile(r"^\d{3}$")


def _resolve_customer_order_store(user):
    if not getattr(user, "is_authenticated", False):
        return None
    preferred_store = getattr(user, "preferred_store", None)
    if preferred_store and preferred_store.is_active:
        return preferred_store
    if getattr(user, "default_region_id", None):
        regional_store = (
            Store.objects.filter(
                region_id=user.default_region_id,
                is_active=True,
            )
            .order_by("name")
            .first()
        )
        if regional_store:
            return regional_store
    return Store.objects.filter(is_active=True).order_by("name").first()


MENU_BASE_IMAGE_ASSETS = {
    "coke": "hero-coke.svg",
    "diet-coke": "hero-coke.svg",
    "coke-zero": "hero-coke.svg",
    "pepsi": "hero-pepsi.svg",
    "diet-pepsi": "hero-pepsi.svg",
    "mountain-dew": "hero-mtn-dew.svg",
    "diet-mountain-dew": "hero-mtn-dew.svg",
    "dr-pepper": "hero-dr-pepper.svg",
    "diet-dr-pepper": "hero-dr-pepper.svg",
    "sprite": "hero-sprite.svg",
    "sprite-zero": "hero-sprite.svg",
    "lemon-lime": "hero-sprite.svg",
    "root-beer": "hero-root-beer.svg",
    "orange-soda": "hero-orange-soda.svg",
    "club-soda": "hero-club-soda.svg",
    "cream-soda": "hero-cream-soda.svg",
}

MENU_BASE_FAMILIES = [
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


def _menu_base_category(base_slug):
    for family in MENU_BASE_FAMILIES:
        if base_slug in family["slugs"]:
            return family["key"], family["label"], family.get("description", "")
    fallback = SODA_OPTIONS.get(base_slug, {})
    return (
        base_slug,
        fallback.get("label", base_slug.replace("-", " ").title()),
        fallback.get("description", ""),
    )


def _menu_item_visual_payload(menu_item):
    base_slug = menu_item.get("default_soda", "")
    base_label = SODA_OPTIONS.get(base_slug, {}).get(
        "label", base_slug.replace("-", " ").title() or "Signature"
    )
    has_float_profile = bool(menu_item.get("default_ice_cream")) or any(
        str(tag).lower() == "float" for tag in menu_item.get("tags", [])
    )
    asset_name = (
        "hero-float.svg"
        if has_float_profile
        else MENU_BASE_IMAGE_ASSETS.get(base_slug, "hero-float.svg")
    )
    return {
        "image_url": static(f"images/drinks/{asset_name}"),
        "image_alt": f"{menu_item.get('name', 'Signature drink')} in an iced cup",
        "base_label": base_label,
    }


def _build_store_menu_sections(*, store):
    cards = []
    categories = {}
    float_cards = []
    for item in get_menu_items():
        base_slug = item.get("default_soda", "")
        category_key, category_label, category_description = _menu_base_category(
            base_slug
        )
        tags = list(item.get("tags", []))
        has_float_profile = bool(item.get("default_ice_cream")) or any(
            str(tag).lower() == "float" for tag in tags
        )
        card = {
            "slug": item["slug"],
            "name": item["name"],
            "description": item.get("description", ""),
            "base_slug": base_slug,
            "category_key": category_key,
            "category_label": category_label,
            "tags": tags[:3],
            "badge": item.get("home_badge", ""),
            "starting_price": item["base_prices"].get("small", ""),
            "customize_url": reverse(
                "orders:customize", args=[store.store_code, item["slug"]]
            ),
            **_menu_item_visual_payload(item),
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
    for family in MENU_BASE_FAMILIES:
        family_section = categories.get(family["key"])
        if family_section:
            family_section["description"] = family.get(
                "description", family_section.get("description", "")
            )
            family_section["count"] = len(family_section["cards"])
            family_section["anchor_id"] = f"menu-section-{family_section['key']}"
            sections.append(family_section)

    family_keys = {family["key"] for family in MENU_BASE_FAMILIES}
    extra_sections = [
        section
        for key, section in categories.items()
        if key not in family_keys and section["cards"]
    ]
    for section in sorted(extra_sections, key=lambda value: value["label"]):
        section["count"] = len(section["cards"])
        section["anchor_id"] = f"menu-section-{section['key']}"
        sections.append(section)

    if float_cards:
        sections.append(
            {
                "key": "floats",
                "label": "Floats",
                "description": "Creamier float builds with ice-cream-forward profiles.",
                "cards": float_cards,
                "count": len(float_cards),
                "anchor_id": "menu-section-floats",
            }
        )

    nav = [
        {
            "key": section["key"],
            "label": section["label"],
            "count": section["count"],
            "anchor_id": section["anchor_id"],
        }
        for section in sections
    ]
    return cards, sections, nav


def _build_menu_hero_recommendations(*, store, latest_result, limit=4):
    menu_items = get_menu_items()
    menu_items_by_slug = {item["slug"]: item for item in menu_items}
    latest_result = latest_result if isinstance(latest_result, dict) else {}
    if not latest_result:
        return []

    prompt = str(latest_result.get("prompt", "")).strip().lower()
    cards = []
    seen_slugs = set()

    def _add_card(
        menu_item,
        *,
        name="",
        description="",
        tags=None,
        badge="",
        selection=None,
    ):
        slug = menu_item.get("slug", "")
        if not slug or slug in seen_slugs:
            return
        seen_slugs.add(slug)
        tags = list(tags or [])
        visual_source = dict(menu_item)
        if selection and selection.get("soda"):
            visual_source["default_soda"] = selection["soda"]
        if selection and selection.get("ice_cream"):
            visual_source["default_ice_cream"] = selection["ice_cream"]
        cards.append(
            {
                "slug": slug,
                "name": name or menu_item.get("name", "Signature Drink"),
                "description": description or menu_item.get("description", ""),
                "base_slug": visual_source.get("default_soda", ""),
                "tags": tags[:2],
                "badge": badge,
                "starting_price": menu_item.get("base_prices", {}).get("small", ""),
                "customize_url": _build_customized_builder_url(
                    store_code=store.store_code, menu_slug=slug, selection=selection
                ),
                **_menu_item_visual_payload(visual_source),
            }
        )

    def _score_menu_item(item):
        if not prompt:
            return 0
        score = 0
        haystack = " ".join(
            [
                item.get("name", ""),
                item.get("description", ""),
                " ".join(item.get("tags", [])),
            ]
        ).lower()
        for token in prompt.split():
            if token and token in haystack:
                score += 2
        for keyword in ("fruity", "fruit", "berry", "refreshing", "citrus"):
            if keyword in prompt and keyword in haystack:
                score += 3
        for keyword in ("float", "creamy", "vanilla", "dessert"):
            if keyword in prompt and keyword in haystack:
                score += 3
        for keyword in ("caffeine-free", "diet", "zero", "lighter"):
            if keyword in prompt and keyword in haystack:
                score += 2
        return score

    drink = latest_result.get("drink") or {}
    if isinstance(drink, dict):
        customizations = drink.get("customizations_json") or {}
        recipe = (
            customizations.get("recipe") if isinstance(customizations, dict) else {}
        )
        if not isinstance(recipe, dict):
            recipe = {}
        starter_slug = drink.get("recipe_key") or recipe.get("starter_menu_slug") or ""
        starter_item = menu_items_by_slug.get(starter_slug)
        if starter_item:
            selection = {
                "size": drink.get("size_snapshot", "medium"),
                "soda": recipe.get("base_soda", ""),
                "syrups": list(recipe.get("syrups", [])),
                "add_ins": list(recipe.get("add_ins", [])),
                "ice_cream": recipe.get("ice_cream", ""),
                "notes": (
                    f"AI prompt: {latest_result.get('prompt', '').strip()}"
                    if latest_result.get("prompt")
                    else ""
                ),
            }
            _add_card(
                starter_item,
                name=drink.get("name", ""),
                description=drink.get("description", "") or recipe.get("reason", ""),
                tags=["AI custom"],
                badge="AI Pick",
                selection=selection,
            )

    for row in latest_result.get("menu_matches", []) or []:
        menu_item = menu_items_by_slug.get(row.get("slug", ""))
        if not menu_item:
            continue
        _add_card(
            menu_item,
            description=row.get("reason", "") or menu_item.get("description", ""),
            tags=["AI match"],
            badge="AI Match",
        )
        if len(cards) >= limit:
            return cards

    if not prompt and not cards:
        return cards

    scored_items = sorted(
        menu_items,
        key=lambda item: (-_score_menu_item(item), item.get("name", "")),
    )
    for menu_item in scored_items:
        if len(cards) >= limit:
            break
        if prompt and _score_menu_item(menu_item) <= 0 and cards:
            continue
        _add_card(menu_item, tags=["AI suggestion"], badge="AI Suggestion")

    return cards[:limit]


def _build_customized_builder_url(*, store_code, menu_slug, selection=None):
    base_url = reverse("orders:customize", args=[store_code, menu_slug])
    if not selection:
        return base_url
    query = []
    size = str(selection.get("size", "")).strip()
    if size in SIZE_LABELS:
        query.append(("size", size))
    soda = str(selection.get("soda", "")).strip()
    if soda in SODA_OPTIONS:
        query.append(("soda", soda))
    for syrup in selection.get("syrups", []):
        if syrup in SYRUP_OPTIONS:
            query.append(("syrups", syrup))
    for add_in in selection.get("add_ins", []):
        if add_in in ADD_IN_OPTIONS:
            query.append(("add_ins", add_in))
    ice_cream = str(selection.get("ice_cream", "")).strip()
    if ice_cream in ICE_CREAM_OPTIONS:
        query.append(("ice_cream", ice_cream))
    notes = str(selection.get("notes", "")).strip()
    if notes:
        query.append(("notes", notes[:180]))
    if not query:
        return base_url
    return f"{base_url}?{urlencode(query, doseq=True)}"


def _attach_menu_ai_builder_url(*, store, response):
    if not isinstance(response, dict):
        return response
    drink = response.get("drink") or {}
    if not isinstance(drink, dict):
        return response
    customizations = drink.get("customizations_json") or {}
    recipe = customizations.get("recipe") if isinstance(customizations, dict) else {}
    if not isinstance(recipe, dict):
        recipe = {}
    starter_menu_slug = drink.get("recipe_key") or recipe.get("starter_menu_slug") or ""
    if not starter_menu_slug:
        return response
    selection = {
        "size": drink.get("size_snapshot", "medium"),
        "soda": recipe.get("base_soda", ""),
        "syrups": list(recipe.get("syrups", [])),
        "add_ins": list(recipe.get("add_ins", [])),
        "ice_cream": recipe.get("ice_cream", ""),
        "notes": (
            f"AI prompt: {response.get('prompt', '').strip()}"
            if response.get("prompt")
            else ""
        ),
    }
    drink["builder_url"] = _build_customized_builder_url(
        store_code=store.store_code,
        menu_slug=starter_menu_slug,
        selection=selection,
    )
    response["drink"] = drink
    return response


def _latest_menu_ai_result_for_store(*, request, store):
    latest_store_code = request.session.get("menu_ai_latest_store_code", "")
    if latest_store_code != store.store_code:
        return {}
    latest_result = request.session.get("menu_ai_latest_result") or {}
    return latest_result if isinstance(latest_result, dict) else {}


def _render_menu_ai_result_response(*, request, store, response):
    response = _attach_menu_ai_builder_url(store=store, response=response)
    html = render_to_string(
        "orders/partials/menu_ai_result.html",
        {
            "menu_ai_result": response,
            "menu_ai_hero_cards": _build_menu_hero_recommendations(
                store=store,
                latest_result=response,
                limit=4,
            ),
            "menu_ai_oob": True,
            "store": store,
        },
        request=request,
    )
    return HttpResponse(html)


def _parse_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _bound_value(form, field_name, fallback=""):
    if form.is_bound:
        return form.data.get(field_name, fallback)
    return form.initial.get(field_name, fallback)


def _bound_list(form, field_name, fallback=None):
    fallback = fallback or []
    if form.is_bound and hasattr(form.data, "getlist"):
        return form.data.getlist(field_name)
    return list(form.initial.get(field_name, fallback) or fallback)


def _customize_initial_from_query(request):
    initial = {}
    size = request.GET.get("size", "").strip()
    if size in SIZE_LABELS:
        initial["size"] = size

    soda = request.GET.get("soda", "").strip()
    if soda in SODA_OPTIONS:
        initial["soda"] = soda

    syrups = [
        token for token in request.GET.getlist("syrups") if token in SYRUP_OPTIONS
    ]
    if syrups:
        initial["syrups"] = syrups

    add_ins = [
        token for token in request.GET.getlist("add_ins") if token in ADD_IN_OPTIONS
    ]
    if add_ins:
        initial["add_ins"] = add_ins

    ice_cream = request.GET.get("ice_cream", "").strip()
    if ice_cream in ICE_CREAM_OPTIONS:
        initial["ice_cream"] = ice_cream

    notes = request.GET.get("notes", "").strip()
    if notes:
        initial["notes"] = notes[:500]

    return initial


def _build_choice_cards(*, name, groups, selected_values, multiple):
    selected_set = set(selected_values)
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
                        "price": item["price"],
                        "checked": item["value"] in selected_set,
                        "multiple": multiple,
                    }
                    for item in group["items"]
                ],
            }
        )
    return payload


def _build_builder_context(*, form, menu_item):
    selected_size = _bound_value(form, "size", "medium")
    selected_soda = _bound_value(form, "soda", menu_item["default_soda"])
    selected_syrups = _bound_list(form, "syrups", menu_item["default_syrups"])
    selected_add_ins = _bound_list(form, "add_ins", menu_item["default_add_ins"])
    selected_ice_cream = _bound_value(
        form, "ice_cream", menu_item.get("default_ice_cream", "")
    )
    builder_pricing = {
        "base_prices": menu_item["base_prices"],
        "syrups": {key: str(option["price"]) for key, option in SYRUP_OPTIONS.items()},
        "add_ins": {
            key: str(option["price"]) for key, option in ADD_IN_OPTIONS.items()
        },
        "ice_cream": {
            key: str(option["price"]) for key, option in ICE_CREAM_OPTIONS.items()
        },
    }
    size_cards = [
        {
            "id": f"id_size_{value}",
            "name": "size",
            "value": value,
            "label": label,
            "checked": value == selected_size,
        }
        for value, label in SIZE_LABELS.items()
    ]
    soda_cards = _build_choice_cards(
        name="soda",
        groups=grouped_options(SODA_OPTIONS, SODA_GROUPS),
        selected_values=[selected_soda],
        multiple=False,
    )
    syrup_cards = _build_choice_cards(
        name="syrups",
        groups=grouped_options(SYRUP_OPTIONS, SYRUP_GROUPS),
        selected_values=selected_syrups,
        multiple=True,
    )
    add_in_cards = _build_choice_cards(
        name="add_ins",
        groups=grouped_options(ADD_IN_OPTIONS, ADD_IN_GROUPS),
        selected_values=selected_add_ins,
        multiple=True,
    )
    ice_cream_cards = [
        {
            "label": group["label"],
            "description": group.get("description", ""),
            "items": [
                {
                    "id": f"id_ice_cream_none",
                    "name": "ice_cream",
                    "value": "",
                    "label": "No ice cream",
                    "description": "Keep it soda-only.",
                    "price": 0,
                    "checked": not selected_ice_cream,
                    "multiple": False,
                }
            ]
            + [
                {
                    "id": f"id_ice_cream_{item['value']}",
                    "name": "ice_cream",
                    "value": item["value"],
                    "label": item["label"],
                    "description": item.get("description", ""),
                    "price": item["price"],
                    "checked": item["value"] == selected_ice_cream,
                    "multiple": False,
                }
                for item in group["items"]
            ],
        }
        for group in grouped_options(ICE_CREAM_OPTIONS, ICE_CREAM_GROUPS)
    ]
    return {
        "size_cards": size_cards,
        "soda_cards": soda_cards,
        "syrup_cards": syrup_cards,
        "add_in_cards": add_in_cards,
        "ice_cream_cards": ice_cream_cards,
        "builder_pricing": builder_pricing,
        "selected_size": selected_size,
        "selected_soda": selected_soda,
        "selected_syrups": selected_syrups,
        "selected_add_ins": selected_add_ins,
        "selected_ice_cream": selected_ice_cream,
    }


class MenuView(CustomerOrderingRequiredMixin, TemplateView):
    template_name = "orders/menu.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        store = get_object_or_404(
            Store, store_code=self.kwargs["store_code"], is_active=True
        )
        latest_menu_ai_result = _latest_menu_ai_result_for_store(
            request=self.request, store=store
        )
        cart = get_cart(self.request.session)
        menu_items, menu_sections, menu_nav = _build_store_menu_sections(store=store)
        context.update(
            {
                "store": store,
                "menu_items": menu_items,
                "menu_sections": menu_sections,
                "menu_nav": menu_nav,
                "cart": cart,
                "cart_item_count": cart_item_count(cart),
                "hero_recommendation_cards": _build_menu_hero_recommendations(
                    store=store,
                    latest_result=latest_menu_ai_result,
                    limit=4,
                ),
                "menu_ai_form": MenuAiPromptForm(),
                "menu_ai_result": _attach_menu_ai_builder_url(
                    store=store,
                    response=latest_menu_ai_result,
                ),
            }
        )
        return context


class MenuAiAssistantView(CustomerOrderingRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        store = get_object_or_404(
            Store, store_code=kwargs["store_code"], is_active=True
        )
        form = MenuAiPromptForm(request.POST)
        if not form.is_valid():
            response = build_menu_ai_assistance(
                user=request.user if request.user.is_authenticated else None,
                store=store,
                prompt="",
                menu_items=get_menu_items(),
            )
            response["answer"] = (
                "Please describe the kind of drink you want so I can help."
            )
        else:
            response = build_menu_ai_assistance(
                user=request.user if request.user.is_authenticated else None,
                store=store,
                prompt=form.cleaned_data["prompt"],
                menu_items=get_menu_items(),
            )
        response = _attach_menu_ai_builder_url(store=store, response=response)

        request.session["menu_ai_latest_result"] = response
        request.session["menu_ai_latest_store_code"] = store.store_code

        return _render_menu_ai_result_response(
            request=request,
            store=store,
            response=response,
        )


class MenuAiSaveView(RoleRequiredMixin, LoginRequiredMixin, View):
    allowed_roles = (User.Role.ACCOUNT_USER,)

    def post(self, request, *args, **kwargs):
        store = get_object_or_404(
            Store, store_code=kwargs["store_code"], is_active=True
        )
        latest_store_code = request.session.get("menu_ai_latest_store_code", "")
        latest_result = request.session.get("menu_ai_latest_result") or {}
        if latest_store_code and latest_store_code != store.store_code:
            latest_result = {}

        drink = latest_result.get("drink") or {}
        if not drink:
            messages.error(request, "Generate a drink first so it can be saved.")
            response = build_menu_ai_assistance(
                user=request.user,
                store=store,
                prompt=latest_result.get("prompt", ""),
                menu_items=get_menu_items(),
            )
            response["saved"] = False
        else:
            favorite = save_favorite_drink(
                user=request.user,
                name=drink["name"],
                recipe_key=drink.get("recipe_key", ""),
                size_snapshot=drink.get("size_snapshot", "medium"),
                base_price_snapshot=Decimal(
                    str(drink.get("base_price_snapshot", "0.00"))
                ),
                customizations_json=drink.get("customizations_json", {}),
                description=drink.get("description", ""),
            )
            messages.success(request, f"Saved {favorite.name} to your favorites.")
            latest_result["saved"] = True
            latest_result["saved_favorite_name"] = favorite.name
            request.session["menu_ai_latest_result"] = latest_result
            response = latest_result

        return _render_menu_ai_result_response(
            request=request,
            store=store,
            response=response,
        )


class MenuAiAddToCartView(CustomerOrderingRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        store = get_object_or_404(
            Store, store_code=kwargs["store_code"], is_active=True
        )
        latest_store_code = request.session.get("menu_ai_latest_store_code", "")
        latest_result = request.session.get("menu_ai_latest_result") or {}
        if latest_store_code and latest_store_code != store.store_code:
            latest_result = {}

        drink = latest_result.get("drink") or {}
        cart_item = drink.get("cart_item") or {}
        if not cart_item:
            messages.error(
                request, "Generate a drink first so it can be added to cart."
            )
            response = build_menu_ai_assistance(
                user=request.user if request.user.is_authenticated else None,
                store=store,
                prompt=latest_result.get("prompt", ""),
                menu_items=get_menu_items(),
            )
            response["added_to_cart"] = False
        else:
            add_cart_item(request.session, store_code=store.store_code, item=cart_item)
            latest_result["added_to_cart"] = True
            latest_result["added_to_cart_name"] = cart_item.get(
                "display_name", "your drink"
            )
            request.session["menu_ai_latest_result"] = latest_result
            response = latest_result
            messages.success(
                request, f"{cart_item.get('display_name', 'Drink')} added to your cart."
            )

        return _render_menu_ai_result_response(
            request=request,
            store=store,
            response=response,
        )


class CustomizeDrinkView(CustomerOrderingRequiredMixin, TemplateView):
    template_name = "orders/customize.html"

    def dispatch(self, request, *args, **kwargs):
        self.store = get_object_or_404(
            Store, store_code=kwargs["store_code"], is_active=True
        )
        self.menu_item = get_menu_item(kwargs["drink_slug"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = kwargs.get("form")
        if not form:
            form = DrinkCustomizationForm(
                initial=_customize_initial_from_query(self.request),
                drink_slug=self.menu_item["slug"],
            )
        builder_context = _build_builder_context(form=form, menu_item=self.menu_item)
        context.update(
            {
                "store": self.store,
                "menu_item": self.menu_item,
                "form": form,
                "assistant": build_drink_builder_assistance(
                    user=self.request.user,
                    menu_item=self.menu_item,
                    size=builder_context["selected_size"],
                    soda=builder_context["selected_soda"],
                    syrups=builder_context["selected_syrups"],
                    add_ins=builder_context["selected_add_ins"],
                    ice_cream=builder_context["selected_ice_cream"],
                ),
                **builder_context,
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        form = DrinkCustomizationForm(request.POST, drink_slug=self.menu_item["slug"])
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form=form))

        cart_item = build_cart_item(
            drink_slug=self.menu_item["slug"],
            size=form.cleaned_data["size"],
            soda=form.cleaned_data["soda"],
            syrups=form.cleaned_data["syrups"],
            add_ins=form.cleaned_data["add_ins"],
            ice_cream=form.cleaned_data["ice_cream"],
            quantity=form.cleaned_data["quantity"],
            notes=form.cleaned_data["notes"],
        )
        cart, replaced_store = add_cart_item(
            request.session,
            store_code=self.store.store_code,
            item=cart_item,
        )
        if replaced_store:
            messages.warning(
                request,
                "Your cart was reset because each order must stay tied to one store.",
            )
        if (
            request.user.is_authenticated
            and request.user.role == User.Role.ACCOUNT_USER
            and request.POST.get("save_favorite")
        ):
            save_favorite_drink(
                user=request.user,
                name=f"{self.menu_item['name']} ({form.cleaned_data['size'].title()})",
                recipe_key=self.menu_item["slug"],
                size_snapshot=form.cleaned_data["size"],
                base_price_snapshot=cart_item["base_price"],
                customizations_json=cart_item["customizations"],
                description=cart_item["description"],
            )
            messages.success(request, "Saved to favorites.")
        messages.success(request, f"Added {self.menu_item['name']} to your cart.")
        return redirect("orders:cart")


class CartView(CustomerOrderingRequiredMixin, TemplateView):
    template_name = "orders/cart.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cart = get_cart(self.request.session)
        store = (
            Store.objects.filter(store_code=cart["store_code"]).first()
            if cart["store_code"]
            else None
        )
        pricing = build_cart_pricing(cart=cart, store=store) if store else None
        context.update(
            {
                "cart": cart,
                "store": store,
                "pricing": pricing,
                "cart_quantity_form": CartQuantityForm(),
            }
        )
        return context


class CartItemUpdateView(CustomerOrderingRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        form = CartQuantityForm(request.POST)
        if form.is_valid():
            update_cart_item(
                request.session, kwargs["item_id"], form.cleaned_data["quantity"]
            )
        cart = get_cart(request.session)
        store = (
            Store.objects.filter(store_code=cart["store_code"]).first()
            if cart["store_code"]
            else None
        )
        pricing = build_cart_pricing(cart=cart, store=store) if store else None
        html = render_to_string(
            "orders/partials/cart_panel.html",
            {
                "cart": cart,
                "store": store,
                "pricing": pricing,
                "cart_quantity_form": CartQuantityForm(),
            },
            request=request,
        )
        return HttpResponse(html)


class CartItemRemoveView(CustomerOrderingRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        remove_cart_item(request.session, kwargs["item_id"])
        cart = get_cart(request.session)
        store = (
            Store.objects.filter(store_code=cart["store_code"]).first()
            if cart["store_code"]
            else None
        )
        pricing = build_cart_pricing(cart=cart, store=store) if store else None
        html = render_to_string(
            "orders/partials/cart_panel.html",
            {
                "cart": cart,
                "store": store,
                "pricing": pricing,
                "cart_quantity_form": CartQuantityForm(),
            },
            request=request,
        )
        return HttpResponse(html)


class CheckoutView(CustomerOrderingRequiredMixin, TemplateView):
    template_name = "orders/checkout.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cart = get_cart(self.request.session)
        store = (
            get_object_or_404(Store, store_code=cart["store_code"])
            if cart["store_code"]
            else None
        )
        pricing = build_cart_pricing(cart=cart, store=store) if store else None
        context.update(
            {
                "cart": cart,
                "store": store,
                "pricing": pricing,
                "form": kwargs.get("form") or CheckoutForm(),
                "payment_mode": get_payment_mode(),
                "payment_mode_is_mock": get_payment_mode() == PaymentMode.MOCK,
                "payment_checkout_flow": getattr(
                    settings, "PAYMENT_CHECKOUT_FLOW", "hosted"
                ),
                "stripe_publishable_key": getattr(
                    settings, "STRIPE_PUBLISHABLE_KEY", ""
                ),
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        cart = get_cart(request.session)
        if not cart["items"]:
            messages.error(request, "Your cart is empty.")
            return redirect("orders:cart")
        store = get_object_or_404(Store, store_code=cart["store_code"])
        mismatched_items = [
            item
            for item in cart["items"]
            if item.get("store_code_snapshot")
            and item.get("store_code_snapshot") != store.store_code
        ]
        if mismatched_items:
            messages.error(
                request,
                "Your cart includes items from a different store. Please rebuild your cart for one store.",
            )
            clear_cart(request.session)
            return redirect("orders:cart")
        form = CheckoutForm(request.POST)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form=form))
        if not request.user.is_authenticated:
            if (
                not form.cleaned_data["guest_name"]
                or not form.cleaned_data["guest_email"]
            ):
                form.add_error(
                    "guest_name",
                    "Guest name and email are required for guest checkout.",
                )
                return self.render_to_response(self.get_context_data(form=form))
            customer = None
            guest_contact = {
                "display_name": form.cleaned_data["guest_name"],
                "email": form.cleaned_data["guest_email"],
                "phone_number": form.cleaned_data["guest_phone_number"],
            }
        else:
            customer = (
                request.user if request.user.role == User.Role.ACCOUNT_USER else None
            )
            guest_contact = None

        pickup_time_requested = form.cleaned_data.get("pickup_time_requested")
        if pickup_time_requested and timezone.is_naive(pickup_time_requested):
            pickup_time_requested = timezone.make_aware(
                pickup_time_requested, timezone.get_current_timezone()
            )

        actor = (
            customer
            if customer
            else (request.user if request.user.is_authenticated else None)
        )
        order = create_order(
            store=store,
            items=cart["items"],
            customer=customer,
            guest_contact=guest_contact,
            pickup_time_requested=pickup_time_requested,
            actor=actor,
        )
        if order.order_type == Order.OrderType.GUEST and hasattr(
            order, "guest_contact"
        ):
            authorize_guest_order_access(request.session, order)
        try:
            payment_flow = initialize_order_checkout(
                order, request=request, actor=actor
            )
        except PaymentGatewayError as exc:
            messages.error(request, str(exc))
            return redirect("orders:detail", order_code=order.public_order_code)
        clear_cart(request.session)
        messages.success(request, payment_flow["message"])
        return redirect(payment_flow["redirect_url"])


class CheckoutValidateView(CustomerOrderingRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        cart = get_cart(request.session)
        store = (
            get_object_or_404(Store, store_code=cart["store_code"])
            if cart["store_code"]
            else None
        )
        pricing = build_cart_pricing(cart=cart, store=store) if store else None
        html = render_to_string(
            "orders/partials/checkout_summary.html",
            {"cart": cart, "store": store, "pricing": pricing},
            request=request,
        )
        return HttpResponse(html)


class OrderConfirmationView(TemplateView):
    template_name = "orders/confirmation.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order = get_object_or_404(
            Order.objects.select_related("store").prefetch_related("items"),
            public_order_code=kwargs["order_code"],
        )
        if not user_can_view_order(
            self.request.user, order, session=self.request.session
        ):
            raise PermissionDenied("This order is outside your access scope.")
        context["order"] = order
        return context


class OrderDetailView(TemplateView):
    template_name = "orders/detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order = get_object_or_404(
            Order.objects.select_related(
                "store", "customer", "payment_transaction"
            ).prefetch_related("items"),
            public_order_code=kwargs["order_code"],
        )
        if not user_can_view_order(
            self.request.user, order, session=self.request.session
        ):
            raise PermissionDenied("This order is outside your access scope.")
        actor = self.request.user if self.request.user.is_authenticated else None
        refund_allowed, refund_message = get_refund_eligibility(order, actor=actor)
        can_cancel = (
            order.status
            in {
                Order.Status.PRICING_VALIDATED,
                Order.Status.PAYMENT_PENDING,
            }
            or refund_allowed
        )
        context.update(
            {
                "order": order,
                "payment_transaction": getattr(order, "payment_transaction", None),
                "can_manage": user_can_transition_order(self.request.user, order),
                "can_cancel": can_cancel,
                "cancel_reason": refund_message,
                "payment_mode": get_payment_mode(),
                "payment_mode_is_mock": get_payment_mode() == PaymentMode.MOCK,
                "payment_checkout_flow": getattr(
                    settings, "PAYMENT_CHECKOUT_FLOW", "hosted"
                ),
                "stripe_publishable_key": getattr(
                    settings, "STRIPE_PUBLISHABLE_KEY", ""
                ),
            }
        )
        return context


class OrderCancelView(View):
    def post(self, request, *args, **kwargs):
        order = get_object_or_404(Order, public_order_code=kwargs["order_code"])
        if not user_can_view_order(request.user, order, session=request.session):
            raise PermissionDenied("This order is outside your access scope.")
        actor = request.user if request.user.is_authenticated else None
        if hasattr(order, "payment_transaction"):
            allowed, reason = get_refund_eligibility(order, actor=actor)
            if not allowed:
                messages.error(request, reason)
                return redirect("orders:detail", order_code=order.public_order_code)
            record_refund(
                order, actor=actor, notes="Canceled from the order status page."
            )
            messages.success(
                request, "Your order was canceled and the refund flow has started."
            )
        else:
            transition_order_status(
                order,
                Order.Status.CANCELED,
                actor=actor,
                reason="Canceled before payment completion.",
            )
            messages.success(request, "Your draft order was canceled.")
        return redirect("orders:detail", order_code=order.public_order_code)


class GuestLookupView(FormView):
    template_name = "orders/lookup.html"
    form_class = GuestLookupForm

    def form_valid(self, form):
        entered_code = form.cleaned_data["lookup_code"].strip().upper()
        guest_orders = Order.objects.select_related("guest_contact").filter(
            order_type=Order.OrderType.GUEST
        )

        order = None
        if PICKUP_COMBO_PATTERN.fullmatch(entered_code):
            matches = list(
                guest_orders.filter(locker_code=entered_code).order_by("-created_at")[
                    :2
                ]
            )
            if len(matches) > 1:
                form.add_error(
                    "lookup_code",
                    "That pickup combo matches multiple orders. Use your order code instead.",
                )
                return self.form_invalid(form)
            if matches:
                order = matches[0]
        if order is None:
            matches = list(
                guest_orders.filter(locker_code=entered_code).order_by("-created_at")[
                    :2
                ]
            )
            if len(matches) > 1:
                form.add_error(
                    "lookup_code",
                    "That locker code matches multiple orders. Use your order code instead.",
                )
                return self.form_invalid(form)
            if matches:
                order = matches[0]
        if order is None:
            order = guest_orders.filter(guest_contact__lookup_code=entered_code).first()
        if order is None:
            order = guest_orders.filter(public_order_code=entered_code).first()
        if order is None:
            form.add_error(
                "lookup_code",
                "We could not find an order with that code. Check your confirmation and try again.",
            )
            return self.form_invalid(form)

        authorize_guest_order_access(self.request.session, order)
        return redirect("orders:detail", order_code=order.public_order_code)


class AccountOrderHistoryView(RoleRequiredMixin, LoginRequiredMixin, TemplateView):
    template_name = "orders/history.html"
    allowed_roles = (User.Role.ACCOUNT_USER,)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["orders"] = account_order_history(self.request.user)
        return context


class FavoriteListView(RoleRequiredMixin, LoginRequiredMixin, TemplateView):
    template_name = "orders/favorites.html"
    allowed_roles = (User.Role.ACCOUNT_USER,)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["favorites"] = self.request.user.favorite_drinks.order_by("name")
        return context


class FavoriteRemoveView(RoleRequiredMixin, LoginRequiredMixin, View):
    allowed_roles = (User.Role.ACCOUNT_USER,)

    def post(self, request, *args, **kwargs):
        favorite = get_object_or_404(
            request.user.favorite_drinks, pk=kwargs["favorite_id"]
        )
        remove_favorite_drink(user=request.user, favorite=favorite)
        messages.success(request, "Favorite removed.")
        return redirect("orders:favorites")


class FavoriteAddToCartView(RoleRequiredMixin, LoginRequiredMixin, View):
    allowed_roles = (User.Role.ACCOUNT_USER,)

    def post(self, request, *args, **kwargs):
        favorite = get_object_or_404(
            request.user.favorite_drinks, pk=kwargs["favorite_id"]
        )
        menu_key = (
            favorite.recipe_key
            or favorite.customizations_json.get("menu_key")
            or "berry-burst"
        )
        cart_item = {
            "menu_key": menu_key,
            "display_name": favorite.name,
            "size": favorite.size_snapshot,
            "base_price": str(favorite.base_price_snapshot),
            "extras_total": str(
                favorite.customizations_json.get("extras_total", "0.00")
            ),
            "quantity": 1,
            "description": favorite.description,
            "customizations": favorite.customizations_json,
        }
        store_code = request.POST.get("store_code") or getattr(
            request.user.preferred_store, "store_code", ""
        )
        if not store_code:
            messages.error(request, "Pick a store before reordering a favorite.")
            return redirect("stores:index")
        add_cart_item(request.session, store_code=store_code, item=cart_item)
        messages.success(request, f"{favorite.name} added to your cart.")
        return redirect("orders:cart")


class RecommendationView(CustomerOrderingRequiredMixin, TemplateView):
    template_name = "orders/recommendations.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order_store = _resolve_customer_order_store(self.request.user)
        menu_items_by_slug = {item["slug"]: item for item in get_menu_items()}
        recommendations = recommend_drinks_for_user(
            self.request.user if self.request.user.is_authenticated else None
        )
        hydrated_recommendations = []
        for recommendation in recommendations:
            row = dict(recommendation)
            menu_item = menu_items_by_slug.get(row.get("slug", "")) or {}
            row.update(_menu_item_visual_payload(menu_item or row))
            hydrated_recommendations.append(row)
        context["recommendations"] = hydrated_recommendations
        context["order_store"] = order_store
        return context


class BuilderAssistantView(CustomerOrderingRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        menu_item = get_menu_item(kwargs["drink_slug"])
        form = DrinkCustomizationForm(request.POST, drink_slug=menu_item["slug"])
        size = request.POST.get("size") or "medium"
        soda = request.POST.get("soda") or menu_item["default_soda"]
        syrups = request.POST.getlist("syrups")
        add_ins = request.POST.getlist("add_ins")
        ice_cream = request.POST.get("ice_cream", "")
        if form.is_valid():
            size = form.cleaned_data["size"]
            soda = form.cleaned_data["soda"]
            syrups = form.cleaned_data["syrups"]
            add_ins = form.cleaned_data["add_ins"]
            ice_cream = form.cleaned_data["ice_cream"]
        html = render_to_string(
            "orders/partials/builder_assistant.html",
            {
                "assistant": build_drink_builder_assistance(
                    user=request.user,
                    menu_item=menu_item,
                    size=size,
                    soda=soda,
                    syrups=syrups,
                    add_ins=add_ins,
                    ice_cream=ice_cream,
                )
            },
            request=request,
        )
        return HttpResponse(html)


class BuilderAiFillView(CustomerOrderingRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        menu_item = get_menu_item(kwargs["drink_slug"])
        form = DrinkCustomizationForm(request.POST, drink_slug=menu_item["slug"])
        current_selection = {
            "size": request.POST.get("size") or "",
            "soda": request.POST.get("soda") or "",
            "syrups": request.POST.getlist("syrups"),
            "add_ins": request.POST.getlist("add_ins"),
            "ice_cream": request.POST.get("ice_cream", ""),
        }
        if form.is_valid():
            current_selection = {
                "size": form.cleaned_data["size"],
                "soda": form.cleaned_data["soda"],
                "syrups": form.cleaned_data["syrups"],
                "add_ins": form.cleaned_data["add_ins"],
                "ice_cream": form.cleaned_data["ice_cream"],
            }

        recommendation = recommend_builder_configuration(
            user=request.user,
            menu_item=menu_item,
            current_selection=current_selection,
        )
        assistant_html = render_to_string(
            "orders/partials/builder_assistant.html",
            {
                "assistant": build_drink_builder_assistance(
                    user=request.user,
                    menu_item=menu_item,
                    size=recommendation["size"],
                    soda=recommendation["soda"],
                    syrups=recommendation["syrups"],
                    add_ins=recommendation["add_ins"],
                    ice_cream=recommendation["ice_cream"],
                    ai_applied=True,
                    ai_reasons=recommendation["reasons"],
                )
            },
            request=request,
        )
        return JsonResponse(
            {
                "selection": {
                    "size": recommendation["size"],
                    "soda": recommendation["soda"],
                    "syrups": recommendation["syrups"],
                    "add_ins": recommendation["add_ins"],
                    "ice_cream": recommendation["ice_cream"],
                },
                "assistant_html": assistant_html,
                "reasons": recommendation["reasons"],
            }
        )


class OrderTransitionView(View):
    new_status = None

    def post(self, request, *args, **kwargs):
        order = get_object_or_404(Order, pk=kwargs["order_id"])
        if not user_can_transition_order(request.user, order):
            raise PermissionDenied("You cannot transition this order.")
        transition_order_status(order, self.new_status, actor=request.user)
        if getattr(request, "htmx", False):
            queue = staff_order_queue(request.user)[:10]
            html = render_to_string(
                "orders/partials/manager_queue_table.html",
                {"orders": queue},
                request=request,
            )
            return HttpResponse(html)
        return redirect("orders:index")


class MarkPreparingView(OrderTransitionView):
    new_status = Order.Status.PREPARING


class MarkReadyView(OrderTransitionView):
    new_status = Order.Status.READY


class MarkPickedUpView(OrderTransitionView):
    new_status = Order.Status.PICKED_UP


class OrderWorkspaceView(RoleRequiredMixin, TemplateView):
    template_name = "orders/staff_orders.html"
    allowed_roles = (
        User.Role.MANAGER,
        User.Role.SUPER_ADMIN,
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queue = staff_order_queue(self.request.user)
        status_filter = self.request.GET.get("status", "").strip()
        scope = scoped_region_store_options(
            self.request.user,
            region_id=self.request.GET.get("region", "").strip(),
            store_id=self.request.GET.get("store", "").strip(),
        )
        date_from = _parse_date(self.request.GET.get("date_from", "").strip())
        date_to = _parse_date(self.request.GET.get("date_to", "").strip())
        queue = queue.filter(store__in=scope["active_store_scope"])
        if status_filter:
            queue = queue.filter(status=status_filter)
        if date_from:
            queue = queue.filter(created_at__date__gte=date_from)
        if date_to:
            queue = queue.filter(created_at__date__lte=date_to)
        context.update(
            {
                "orders": queue,
                "status_filter": status_filter,
                "region_options": scope["region_options"],
                "store_options": scope["store_options"],
                "selected_region": scope["selected_region"],
                "selected_store": scope["selected_store"],
                "date_from": date_from.isoformat() if date_from else "",
                "date_to": date_to.isoformat() if date_to else "",
                "status_choices": [
                    Order.Status.QUEUED,
                    Order.Status.PREPARING,
                    Order.Status.READY,
                ],
            }
        )
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        if getattr(request, "htmx", False):
            return render(request, "orders/partials/manager_queue_table.html", context)
        return self.render_to_response(context)

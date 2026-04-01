from __future__ import annotations

import json
import logging
import time
import uuid
from functools import lru_cache
from pathlib import Path
from urllib import error as url_error
from urllib import request as url_request

from django.conf import settings
from apps.users.models import User

from .catalog import (
    ADD_IN_OPTIONS,
    ICE_CREAM_OPTIONS,
    MENU_ITEMS,
    SODA_OPTIONS,
    SYRUP_OPTIONS,
    build_cart_item,
    ingredient_label,
)
from .personalization import build_user_taste_profile, recommend_builder_configuration

logger = logging.getLogger(__name__)
INGREDIENT_CATALOG_PATH = Path(__file__).resolve().parent / "data" / "ingredients.json"

MENU_AI_FALLBACK_PROMPTS = [
    "I want something fruity and refreshing",
    "I want a classic creamy float",
    "I want a caffeine-free drink",
    "I want something bold but not too sweet",
]


def build_drink_builder_assistance(
    *,
    user,
    menu_item,
    size,
    soda,
    syrups,
    add_ins,
    ice_cream="",
    ai_applied=False,
    ai_reasons=None,
):
    profile = build_user_taste_profile(user)
    suggested_fill = recommend_builder_configuration(
        user=user,
        menu_item=menu_item,
        current_selection={
            "size": size,
            "soda": soda,
            "syrups": list(syrups or []),
            "add_ins": list(add_ins or []),
            "ice_cream": ice_cream or "",
        },
    )

    selected_soda_label = SODA_OPTIONS[soda]["label"]
    selected_syrups = [
        SYRUP_OPTIONS[token]["label"] for token in syrups if token in SYRUP_OPTIONS
    ]
    selected_add_ins = [
        ADD_IN_OPTIONS[token]["label"] for token in add_ins if token in ADD_IN_OPTIONS
    ]
    selected_ice_cream = (
        ICE_CREAM_OPTIONS[ice_cream]["label"] if ice_cream in ICE_CREAM_OPTIONS else ""
    )

    if ai_applied and ai_reasons:
        summary = "FloatStack AI filled the builder with a recommendation you can still edit freely."
        tips = list(ai_reasons)
    elif selected_ice_cream:
        summary = f"This build leans into float territory with {selected_soda_label} and {selected_ice_cream.lower()} ice cream."
        tips = [
            "You can still lighten the cup by swapping to a zero-sugar or citrus base."
        ]
    elif selected_syrups or selected_add_ins:
        summary = f"Your current cup starts with {selected_soda_label} and already has a clear flavor direction."
        tips = []
    else:
        summary = f"You have a clean {selected_soda_label.lower()} base. Let FloatStack AI fill the rest if you want a stronger starting point."
        tips = []

    if not ai_applied:
        if not selected_syrups and suggested_fill["syrups"]:
            tips.append(
                f"AI would start with {', '.join(ingredient_label(token) for token in suggested_fill['syrups'])} for a cleaner signature mix."
            )
        if not selected_add_ins and suggested_fill["add_ins"]:
            tips.append(
                f"A finishing touch like {', '.join(ingredient_label(token) for token in suggested_fill['add_ins'])} would round out the texture."
            )
        if not selected_ice_cream and suggested_fill["ice_cream"]:
            tips.append(
                f"If you want more float energy, {ingredient_label(suggested_fill['ice_cream'])} ice cream fits this build well."
            )
        if "dairy-free" in profile["dietary_preferences"]:
            tips.append(
                "Your dairy-free preference is active, so creamy dairy add-ins stay out of AI suggestions."
            )
        elif profile["favorite_add_ins"] and not selected_add_ins:
            next_add_in = sorted(profile["favorite_add_ins"])[0]
            tips.append(
                f"You often lean toward {ingredient_label(next_add_in)} in saved preferences."
            )

    selected_snapshot = [selected_soda_label]
    selected_snapshot.extend(selected_syrups)
    selected_snapshot.extend(selected_add_ins)
    if selected_ice_cream:
        selected_snapshot.append(f"{selected_ice_cream} ice cream")

    return {
        "title": "FloatStack AI",
        "summary": summary,
        "tips": tips[:3],
        "size_label": size.title(),
        "selected_snapshot": selected_snapshot,
        "ai_button_label": "Refine with AI" if ai_applied else "AI Help Me Build It",
        "ai_applied": ai_applied,
        "uses_preferences": bool(_authenticated_preferences(user)),
    }


def build_menu_ai_assistance(*, user, store, prompt, menu_items=None):
    menu_items = list(menu_items or MENU_ITEMS)
    prompt = (prompt or "").strip()
    ingredient_catalog = _load_ingredient_catalog()

    if not prompt:
        return {
            "title": "FloatStack Menu AI",
            "prompt": "",
            "answer": "Tell me the drink vibe you want and I will suggest a few menu options.",
            "quick_prompts": MENU_AI_FALLBACK_PROMPTS,
            "recipe": None,
            "drink": None,
            "menu_matches": [],
            "can_save": False,
            "uses_ai": False,
        }

    anthropic_result = _call_anthropic_menu_ai(
        user=user,
        store=store,
        prompt=prompt,
        menu_items=menu_items,
        ingredient_catalog=ingredient_catalog,
    )
    if anthropic_result:
        return anthropic_result

    fallback_recipe = _build_fallback_recipe(prompt, ingredient_catalog, menu_items)
    fallback_matches = _menu_match_suggestions(prompt, menu_items)
    fallback_drink = _build_menu_ai_drink_payload(
        prompt=prompt,
        store=store,
        recipe=fallback_recipe,
        menu_items=menu_items,
        uses_ai=False,
    )
    answer = _build_fallback_answer(prompt, fallback_recipe, fallback_matches)
    return {
        "title": "FloatStack Menu AI",
        "prompt": prompt,
        "answer": answer,
        "quick_prompts": MENU_AI_FALLBACK_PROMPTS,
        "recipe": fallback_recipe,
        "drink": fallback_drink,
        "menu_matches": fallback_matches,
        "can_save": bool(getattr(user, "is_authenticated", False) and getattr(user, "role", None) == User.Role.ACCOUNT_USER),
        "uses_ai": False,
    }


def _authenticated_preferences(user):
    return bool(
        getattr(user, "is_authenticated", False)
        and getattr(user, "role", None) == User.Role.ACCOUNT_USER
        and user.taste_preferences.exists()
    )


@lru_cache(maxsize=1)
def _load_ingredient_catalog():
    try:
        return json.loads(INGREDIENT_CATALOG_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return _build_ingredient_catalog_payload()


def _build_ingredient_catalog_payload():
    return {
        "sodas": _serialize_ingredient_options(SODA_OPTIONS, "soda"),
        "syrups": _serialize_ingredient_options(SYRUP_OPTIONS, "syrup"),
        "add_ins": _serialize_ingredient_options(ADD_IN_OPTIONS, "add_in"),
        "ice_cream": _serialize_ingredient_options(ICE_CREAM_OPTIONS, "ice_cream"),
    }


def _serialize_ingredient_options(options, category):
    serialized = []
    for slug, option in options.items():
        serialized.append(
            {
                "slug": slug,
                "label": option["label"],
                "price": str(option["price"]),
                "tags": list(option.get("tags", ())),
                "description": option.get("description", ""),
                "category": category,
            }
        )
    return serialized


def _ingredient_lookup_maps(ingredient_catalog):
    return {
        "sodas": {row["slug"]: row for row in ingredient_catalog.get("sodas", [])},
        "syrups": {row["slug"]: row for row in ingredient_catalog.get("syrups", [])},
        "add_ins": {row["slug"]: row for row in ingredient_catalog.get("add_ins", [])},
        "ice_cream": {row["slug"]: row for row in ingredient_catalog.get("ice_cream", [])},
    }


def _ingredient_label_from_lookup(lookup, category, slug):
    item = lookup.get(category, {}).get(slug)
    return item["label"] if item else slug


def _build_fallback_recipe(prompt, ingredient_catalog, menu_items):
    lookups = _ingredient_lookup_maps(ingredient_catalog)
    base_soda = _pick_catalog_item(prompt, ingredient_catalog.get("sodas", []), preferred_keywords=("fruity", "refreshing", "citrus", "bold", "creamy", "caffeine-free"))
    syrup_one = _pick_catalog_item(prompt, ingredient_catalog.get("syrups", []), preferred_keywords=("fruity", "sweet", "berry", "vanilla", "citrus"))
    syrup_two = _pick_catalog_item(prompt + " extra", ingredient_catalog.get("syrups", []), excluded_slugs={syrup_one.get("slug", "")}, preferred_keywords=("mint", "lime", "cherry", "strawberry", "coconut")) if syrup_one else {}
    add_in = _pick_catalog_item(prompt, ingredient_catalog.get("add_ins", []), preferred_keywords=("cream", "mint", "vanilla", "coconut", "fruit"))
    ice_cream = _pick_catalog_item(prompt, ingredient_catalog.get("ice_cream", []), preferred_keywords=("float", "creamy", "dessert", "vanilla"))
    starter_menu_item = _best_menu_match_for_base(base_soda.get("slug", ""), menu_items)

    recipe_name = _build_recipe_name(prompt, base_soda, syrup_one, syrup_two, add_in, ice_cream)
    recipe_description = _build_recipe_description(prompt, base_soda, syrup_one, syrup_two, add_in, ice_cream)
    recipe_reason = _build_recipe_reason(prompt, base_soda, syrup_one, syrup_two, add_in, ice_cream)

    return {
        "name": recipe_name,
        "description": recipe_description,
        "reason": recipe_reason,
        "base_soda": base_soda,
        "syrups": [item for item in [syrup_one, syrup_two] if item],
        "add_ins": [add_in] if add_in else [],
        "ice_cream": ice_cream or None,
        "starter_menu_item": starter_menu_item,
        "quick_prompts": MENU_AI_FALLBACK_PROMPTS,
    }


def _pick_catalog_item(prompt, items, *, preferred_keywords=(), excluded_slugs=None):
    excluded_slugs = set(excluded_slugs or [])
    prompt_lower = (prompt or "").lower()
    best_item = None
    best_score = -1
    for item in items:
        slug = item.get("slug", "")
        if slug in excluded_slugs:
            continue
        score = 0
        haystack = " ".join([item.get("label", ""), item.get("description", ""), " ".join(item.get("tags", []))]).lower()
        for keyword in preferred_keywords:
            if keyword in prompt_lower:
                if keyword in haystack:
                    score += 3
        for token in prompt_lower.split():
            if token and token in haystack:
                score += 1
        for tag in item.get("tags", []):
            if tag in prompt_lower:
                score += 2
        if score > best_score:
            best_score = score
            best_item = item
    return best_item or (items[0] if items else {})


def _best_menu_match_for_base(base_slug, menu_items):
    if not base_slug:
        return {}
    base = base_slug.replace("diet-", "").replace("-zero", "")
    for item in menu_items:
        slug = item.get("slug", "")
        if base in slug or slug in base:
            return item
    return menu_items[0] if menu_items else {}


def _build_recipe_name(prompt, base_soda, syrup_one, syrup_two, add_in, ice_cream):
    parts = []
    lower_prompt = (prompt or "").lower()
    if any(word in lower_prompt for word in ["fruity", "berry", "fruit"]):
        parts.append("Berry")
    elif any(word in lower_prompt for word in ["citrus", "lemon", "lime", "refreshing"]):
        parts.append("Citrus")
    elif any(word in lower_prompt for word in ["creamy", "float", "vanilla"]):
        parts.append("Float")
    elif any(word in lower_prompt for word in ["bold", "spiced", "cola"]):
        parts.append("Bold")
    else:
        parts.append("Custom")
    parts.append(base_soda.get("label", "Soda"))
    if ice_cream:
        parts.append("Float")
    return " ".join(parts)


def _build_recipe_description(prompt, base_soda, syrup_one, syrup_two, add_in, ice_cream):
    ingredients = [base_soda.get("label", "")]
    for item in (syrup_one, syrup_two, add_in):
        if item and item.get("label"):
            ingredients.append(item["label"])
    if ice_cream and ice_cream.get("label"):
        ingredients.append(ice_cream["label"])
    ingredients = [item for item in ingredients if item]
    return f"Start with {', '.join(ingredients[:-1])} and finish with {ingredients[-1]}." if len(ingredients) > 1 else f"Start with {ingredients[0]} and build from there."


def _build_recipe_reason(prompt, base_soda, syrup_one, syrup_two, add_in, ice_cream):
    prompt_lower = (prompt or "").lower()
    if any(word in prompt_lower for word in ["fruity", "berry", "fruit"]):
        return "Built to feel bright and fruit-forward while staying within the current ingredient list."
    if any(word in prompt_lower for word in ["creamy", "float", "vanilla"]):
        return "Built to lean creamy and float-like without leaving the catalog ingredients."
    if any(word in prompt_lower for word in ["caffeine-free", "no caffeine"]):
        return "Built from caffeine-free ingredients for a lighter custom drink."
    return "Built from existing ingredients to give you something new to try."
def _call_anthropic_menu_ai(*, user, store, prompt, menu_items, ingredient_catalog):
    api_key = str(getattr(settings, "ANTHROPIC_API_KEY", "") or "").strip()
    if not api_key:
        return None

    base_url = str(
        getattr(settings, "ANTHROPIC_API_BASE_URL", "https://api.anthropic.com")
    ).rstrip("/")
    model = str(getattr(settings, "ANTHROPIC_MODEL", "claude-3-5-haiku-latest"))
    timeout_seconds = float(getattr(settings, "AI_PROVIDER_TIMEOUT_SECONDS", 8))
    max_retries = int(getattr(settings, "AI_PROVIDER_MAX_RETRIES", 2))

    menu_context = [
        {
            "slug": item["slug"],
            "name": item["name"],
            "description": item["description"],
            "tags": list(item.get("tags", [])),
        }
        for item in menu_items[:10]
    ]
    user_role = getattr(user, "role", "guest") if getattr(user, "is_authenticated", False) else "guest"
    system_prompt = (
        "You are FloatStack Menu AI, a concise assistant that creates a custom soda suggestion from the provided ingredient catalog. "
        "Only use the ingredient catalog and menu context provided to you. Do not invent ingredients, prices, or menu items. "
        "Respect FloatStack rules: orders stay scoped to one store, and you are only helping choose a drink. "
        "Return JSON only with this exact shape: {\"answer\": string, \"recipe\": {\"name\": string, \"description\": string, \"reason\": string, \"base_soda_slug\": string, \"syrup_slugs\": [string, ...], \"add_in_slugs\": [string, ...], \"ice_cream_slug\": string, \"starter_menu_slug\": string}, \"quick_prompts\": [string, ...], \"menu_matches\": [{\"slug\": string, \"reason\": string}]}. "
        "Choose existing ingredients only. Keep the answer friendly and under 120 words."
    )
    body = {
        "model": model,
        "max_tokens": 400,
        "messages": [
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "store": {
                            "name": getattr(store, "name", ""),
                            "code": getattr(store, "store_code", ""),
                        },
                        "user_role": user_role,
                        "prompt": prompt,
                        "ingredient_catalog": ingredient_catalog,
                        "menu_items": menu_context,
                    }
                ),
            }
        ],
        "system": system_prompt,
    }

    for attempt in range(max_retries + 1):
        started_at = time.perf_counter()
        try:
            req = url_request.Request(
                url=f"{base_url}/v1/messages",
                data=json.dumps(body).encode("utf-8"),
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                method="POST",
            )
            with url_request.urlopen(req, timeout=timeout_seconds) as resp:
                payload = json.loads(resp.read().decode("utf-8"))

            text_block = ""
            for block in payload.get("content") or []:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_block = block.get("text", "")
                    break
            if not text_block:
                raise ValueError("Anthropic response did not contain text content.")

            parsed = json.loads(text_block)
            recipe = _normalize_recipe(parsed.get("recipe") or {}, ingredient_catalog, menu_items)
            menu_matches = _normalize_menu_matches(parsed.get("menu_matches") or [], menu_items)
            drink = _build_menu_ai_drink_payload(
                prompt=prompt,
                store=store,
                recipe=recipe,
                menu_items=menu_items,
                uses_ai=True,
            )
            return {
                "title": "FloatStack Menu AI",
                "prompt": prompt,
                "answer": str(parsed.get("answer", "")).strip() or _build_fallback_answer(prompt, recipe, menu_matches),
                "quick_prompts": [
                    str(item).strip()
                    for item in (parsed.get("quick_prompts") or MENU_AI_FALLBACK_PROMPTS)
                    if str(item).strip()
                ][:4],
                "recipe": recipe,
                "drink": drink,
                "menu_matches": menu_matches,
                "can_save": bool(getattr(user, "is_authenticated", False) and getattr(user, "role", None) == User.Role.ACCOUNT_USER),
                "uses_ai": True,
            }
        except (ValueError, json.JSONDecodeError, TimeoutError, url_error.URLError, url_error.HTTPError) as exc:
            logger.warning(
                "menu_ai_provider_attempt_failed",
                extra={
                    "attempt": attempt,
                    "latency_ms": int((time.perf_counter() - started_at) * 1000),
                    "error": exc.__class__.__name__,
                    "model": model,
                },
            )
            if attempt >= max_retries:
                break
            time.sleep(min(0.5 * (2**attempt), 2))

    return None


def _build_menu_ai_drink_payload(*, prompt, store, recipe, menu_items, uses_ai):
    starter_menu_item = recipe.get("starter_menu_item") or _best_menu_match_for_base(
        (recipe.get("base_soda") or {}).get("slug", ""), menu_items
    )
    base_name = str(recipe.get("name", "Custom Drink")).strip() or "Custom Drink"
    drink_name = _make_unique_drink_name(base_name=base_name, prompt=prompt)
    size_snapshot = "medium"
    base_soda_slug = (recipe.get("base_soda") or {}).get("slug", "")
    syrup_slugs = [item.get("slug", "") for item in recipe.get("syrups", []) if item.get("slug")]
    add_in_slugs = [item.get("slug", "") for item in recipe.get("add_ins", []) if item.get("slug")]
    ice_cream_slug = (
        (recipe.get("ice_cream") or {}).get("slug", "")
        if isinstance(recipe.get("ice_cream"), dict)
        else ""
    )
    menu_key = starter_menu_item.get("slug", "")
    cart_item = (
        build_cart_item(
            drink_slug=menu_key,
            size=size_snapshot,
            soda=base_soda_slug or starter_menu_item.get("default_soda", "sprite"),
            syrups=syrup_slugs,
            add_ins=add_in_slugs,
            ice_cream=ice_cream_slug,
            quantity=1,
            notes=f"AI-generated from prompt: {prompt}",
        )
        if menu_key
        else {
            "menu_key": "",
            "display_name": drink_name,
            "size": size_snapshot,
            "base_price": "0.00",
            "extras_total": "0.00",
            "quantity": 1,
            "description": str(recipe.get("description", "")).strip(),
            "customizations": {
                "soda": base_soda_slug,
                "syrups": syrup_slugs,
                "add_ins": add_in_slugs,
                "ice_cream": ice_cream_slug,
                "notes": f"AI-generated from prompt: {prompt}",
                "inventory_requirements": [],
            },
        }
    )
    cart_item["display_name"] = drink_name

    base_price_snapshot = str(cart_item.get("base_price", "0.00"))
    extras_total = str(cart_item.get("extras_total", "0.00"))
    customizations_json = {
        "schema_version": 1,
        "source": "anthropic" if uses_ai else "local",
        "ai_generated": bool(uses_ai),
        "store": {
            "code": getattr(store, "store_code", ""),
            "name": getattr(store, "name", ""),
        },
        "prompt": prompt,
        "menu_key": menu_key,
        "recipe": {
            "name": drink_name,
            "description": str(recipe.get("description", "")).strip(),
            "reason": str(recipe.get("reason", "")).strip(),
            "base_soda": base_soda_slug,
            "syrups": syrup_slugs,
            "add_ins": add_in_slugs,
            "ice_cream": ice_cream_slug,
            "starter_menu_slug": menu_key,
        },
        "extras_total": extras_total,
        "ingredient_labels": {
            "base_soda": (recipe.get("base_soda") or {}).get("label", ""),
            "syrups": [item.get("label", "") for item in recipe.get("syrups", []) if item.get("label")],
            "add_ins": [item.get("label", "") for item in recipe.get("add_ins", []) if item.get("label")],
            "ice_cream": (recipe.get("ice_cream") or {}).get("label", "") if isinstance(recipe.get("ice_cream"), dict) else "",
        },
        "starter_menu": {
            "slug": menu_key,
            "name": starter_menu_item.get("name", ""),
            "description": starter_menu_item.get("description", ""),
        },
    }
    return {
        "name": drink_name,
        "recipe_key": menu_key,
        "size_snapshot": size_snapshot,
        "base_price_snapshot": base_price_snapshot,
        "description": str(recipe.get("description", "")).strip() or "A custom drink built from the current ingredient list.",
        "extras_total": extras_total,
        "cart_item": cart_item,
        "customizations_json": customizations_json,
    }


def _make_unique_drink_name(*, base_name, prompt):
    normalized = " ".join(str(base_name or "Custom Drink").split())
    prompt_seed = "".join(ch for ch in str(prompt or "").lower() if ch.isalnum())
    short_seed = prompt_seed[:2].upper() if prompt_seed else "CP"
    unique_suffix = uuid.uuid4().hex[:4].upper()
    return f"{normalized} {short_seed}-{unique_suffix}"


def _normalize_recipe(raw_recipe, ingredient_catalog, menu_items):
    lookups = _ingredient_lookup_maps(ingredient_catalog)
    base_soda_slug = str(raw_recipe.get("base_soda_slug", "")).strip()
    syrup_slugs = [str(slug).strip() for slug in raw_recipe.get("syrup_slugs") or [] if str(slug).strip()]
    add_in_slugs = [str(slug).strip() for slug in raw_recipe.get("add_in_slugs") or [] if str(slug).strip()]
    ice_cream_slug = str(raw_recipe.get("ice_cream_slug", "")).strip()
    starter_menu_slug = str(raw_recipe.get("starter_menu_slug", "")).strip()

    base_soda = lookups["sodas"].get(base_soda_slug) or next(iter(lookups["sodas"].values()), {})
    syrups = [lookups["syrups"].get(slug) for slug in syrup_slugs if lookups["syrups"].get(slug)]
    add_ins = [lookups["add_ins"].get(slug) for slug in add_in_slugs if lookups["add_ins"].get(slug)]
    ice_cream = lookups["ice_cream"].get(ice_cream_slug)
    starter_menu_item = next((item for item in menu_items if item.get("slug") == starter_menu_slug), {})

    return {
        "name": str(raw_recipe.get("name", "Custom Drink")).strip() or "Custom Drink",
        "description": str(raw_recipe.get("description", "")).strip() or "A custom drink built from the current ingredient list.",
        "reason": str(raw_recipe.get("reason", "")).strip() or "Built from existing ingredients.",
        "base_soda": base_soda,
        "syrups": syrups,
        "add_ins": add_ins,
        "ice_cream": ice_cream,
        "starter_menu_item": starter_menu_item,
        "quick_prompts": MENU_AI_FALLBACK_PROMPTS,
    }


def _menu_match_suggestions(prompt, menu_items):
    lowered = (prompt or "").lower()
    scored = []
    for item in menu_items:
        score = 0
        haystack = " ".join(
            [item.get("name", ""), item.get("description", ""), " ".join(item.get("tags", []))]
        ).lower()
        for token in lowered.split():
            if token and token in haystack:
                score += 2
        for keyword in ("fruit", "fruity", "berry", "citrus", "refreshing"):
            if keyword in lowered and keyword in haystack:
                score += 3
        for keyword in ("creamy", "float", "dessert", "vanilla"):
            if keyword in lowered and keyword in haystack:
                score += 3
        if not score and any(tag in lowered for tag in item.get("tags", [])):
            score += 1
        scored.append((score, item))

    scored.sort(key=lambda row: (-row[0], row[1].get("name", "")))
    matches = []
    for score, item in scored[:3]:
        if score <= 0 and matches:
            break
        matches.append(
            {
                "slug": item.get("slug", ""),
                "name": item.get("name", ""),
                "description": item.get("description", ""),
                "reason": _build_match_reason(prompt, item),
            }
        )
    return matches


def _normalize_menu_matches(raw_matches, menu_items):
    by_slug = {item.get("slug", ""): item for item in menu_items}
    by_name = {item.get("name", "").lower(): item for item in menu_items}
    normalized = []
    seen = set()
    for row in raw_matches:
        if isinstance(row, dict):
            slug = str(row.get("slug", "")).strip()
            name = str(row.get("name", "")).strip().lower()
            item = by_slug.get(slug) or by_name.get(name)
            if not item:
                continue
            resolved_slug = item.get("slug", "")
            if resolved_slug in seen:
                continue
            seen.add(resolved_slug)
            normalized.append(
                {
                    "slug": resolved_slug,
                    "name": item.get("name", ""),
                    "description": item.get("description", ""),
                    "reason": str(row.get("reason", "")).strip() or _build_match_reason("", item),
                }
            )
    return normalized


def _build_match_reason(prompt, item):
    prompt_lower = (prompt or "").lower()
    tags = set(item.get("tags", []))
    if any(token in prompt_lower for token in ["fruity", "fruit", "berry", "refreshing"]):
        if "fruit" in tags or "citrus" in tags:
            return "Fits a bright, refreshing request."
    if any(token in prompt_lower for token in ["creamy", "float", "dessert"]):
        if "float-friendly" in tags or "dessert" in tags or "creamy" in tags:
            return "Matches the creamy float vibe."
    if any(token in prompt_lower for token in ["caffeine-free", "no caffeine", "decaf"]):
        if "caffeine-free" in tags:
            return "Keeps the drink caffeine-free."
    if any(token in prompt_lower for token in ["zero sugar", "diet", "lighter"]):
        if "zero-sugar" in tags or "diet" in tags:
            return "Supports a lighter zero-sugar build."
    return f"Good match for {item.get('name', '')}."


def _build_fallback_answer(prompt, recipe, menu_matches):
    if recipe:
        base_label = recipe.get("base_soda", {}).get("label", "a soda base")
        add_in_labels = [item.get("label", "") for item in recipe.get("add_ins", []) if item.get("label")]
        syrup_labels = [item.get("label", "") for item in recipe.get("syrups", []) if item.get("label")]
        ice_cream_label = recipe.get("ice_cream", {}).get("label", "") if isinstance(recipe.get("ice_cream"), dict) else ""
        ingredient_bits = [base_label] + syrup_labels + add_in_labels
        if ice_cream_label:
            ingredient_bits.append(ice_cream_label)
        ingredient_bits = [item for item in ingredient_bits if item]
        if ingredient_bits:
            core = ", ".join(ingredient_bits[:3])
            if len(ingredient_bits) > 3:
                core = f"{core}, and {ingredient_bits[3]}"
            return f"Try this custom mix: {recipe.get('name', 'Custom Drink')} with {core}. {recipe.get('reason', '')}".strip()
    if not menu_matches:
        return (
            "I would start with a crisp citrus or classic cola base, then add one flavor layer and keep the build simple."
        )
    names = [row["name"] for row in menu_matches[:3] if row.get("name")]
    if len(names) == 1:
        return f"I would start with {names[0]} for that request, then customize from there."
    if len(names) == 2:
        return f"I would start with {names[0]} or {names[1]} for that request."
    return f"I would start with {names[0]}, {names[1]}, or {names[2]} for that request."

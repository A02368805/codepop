from __future__ import annotations

from collections import Counter

from apps.users.models import TastePreference, User

from .catalog import (
    ADD_IN_OPTIONS,
    ICE_CREAM_OPTIONS,
    MENU_ITEMS,
    SODA_OPTIONS,
    SYRUP_OPTIONS,
)


def _authenticated_account_user(user):
    return bool(
        getattr(user, "is_authenticated", False)
        and getattr(user, "role", None) == User.Role.ACCOUNT_USER
    )


def _seed_profile():
    return {
        "favorite_sodas": set(),
        "favorite_syrups": set(),
        "favorite_add_ins": set(),
        "favorite_ice_creams": set(),
        "dislikes": set(),
        "dietary_preferences": set(),
        "sweetness_preference": User.SweetnessPreference.BALANCED,
        "adventurousness_preference": User.AdventurousnessPreference.BALANCED,
        "favorite_recipe_keys": set(),
        "soda_counter": Counter(),
        "syrup_counter": Counter(),
        "add_in_counter": Counter(),
        "ice_cream_counter": Counter(),
        "size_counter": Counter(),
    }


def build_user_taste_profile(user):
    profile = _seed_profile()
    if not _authenticated_account_user(user):
        return profile

    preferences = list(user.taste_preferences.all())
    for preference in preferences:
        token = preference.ingredient_name
        if preference.preference_type in {
            TastePreference.PreferenceType.DISLIKE,
            TastePreference.PreferenceType.LIKE,
        }:
            if preference.preference_type == TastePreference.PreferenceType.DISLIKE:
                profile["dislikes"].add(token)
            elif token in SODA_OPTIONS:
                profile["favorite_sodas"].add(token)
            elif token in SYRUP_OPTIONS:
                profile["favorite_syrups"].add(token)
            elif token in ADD_IN_OPTIONS:
                profile["favorite_add_ins"].add(token)
            elif token in ICE_CREAM_OPTIONS:
                profile["favorite_ice_creams"].add(token)
            continue

        if preference.preference_type == TastePreference.PreferenceType.FAVORITE_SODA:
            profile["favorite_sodas"].add(token)
        elif (
            preference.preference_type == TastePreference.PreferenceType.FAVORITE_SYRUP
        ):
            profile["favorite_syrups"].add(token)
        elif (
            preference.preference_type == TastePreference.PreferenceType.FAVORITE_ADD_IN
        ):
            profile["favorite_add_ins"].add(token)
        elif (
            preference.preference_type
            == TastePreference.PreferenceType.FAVORITE_ICE_CREAM
        ):
            profile["favorite_ice_creams"].add(token)
        elif preference.preference_type == TastePreference.PreferenceType.DIETARY:
            profile["dietary_preferences"].add(token)

    profile["sweetness_preference"] = user.sweetness_preference
    profile["adventurousness_preference"] = user.adventurousness_preference

    for favorite in user.favorite_drinks.all()[:8]:
        profile["favorite_recipe_keys"].add(favorite.recipe_key)
        customizations = favorite.customizations_json or {}
        _ingest_customizations(profile, customizations, weight=3)
        if favorite.size_snapshot:
            profile["size_counter"][favorite.size_snapshot] += 2

    recent_orders = user.orders.prefetch_related("items").order_by("-created_at")[:10]
    for order in recent_orders:
        for item in order.items.all():
            _ingest_customizations(profile, item.customizations_json or {}, weight=1)
            if item.size_snapshot:
                profile["size_counter"][item.size_snapshot] += 1

    return profile


def _ingest_customizations(profile, customizations, *, weight):
    soda = customizations.get("soda")
    if soda in SODA_OPTIONS:
        profile["soda_counter"][soda] += weight
    for syrup in customizations.get("syrups") or []:
        if syrup in SYRUP_OPTIONS:
            profile["syrup_counter"][syrup] += weight
    for add_in in customizations.get("add_ins") or []:
        if add_in in ADD_IN_OPTIONS:
            profile["add_in_counter"][add_in] += weight
    ice_cream = customizations.get("ice_cream")
    if ice_cream in ICE_CREAM_OPTIONS:
        profile["ice_cream_counter"][ice_cream] += weight


def _option_allowed(option, dietary_preferences):
    tags = set(option["tags"])
    if "dairy-free" in dietary_preferences and "dairy" in tags:
        return False
    if "caffeine-free" in dietary_preferences and "caffeinated" in tags:
        return False
    if (
        "zero-sugar" in dietary_preferences
        and "zero-sugar" not in tags
        and "diet" not in tags
    ):
        return False
    if "citrus-free" in dietary_preferences and "citrus" in tags:
        return False
    return True


def _pick_best(
    tokens, option_map, preferred_tokens, counter, dietary_preferences, fallback=None
):
    candidates = []
    for token, option in option_map.items():
        if not _option_allowed(option, dietary_preferences):
            continue
        score = counter[token]
        if token in preferred_tokens:
            score += 5
        candidates.append((score, token))
    if not candidates:
        return fallback
    candidates.sort(key=lambda row: (-row[0], option_map[row[1]]["label"]))
    top_score, token = candidates[0]
    if top_score <= 0 and fallback:
        return fallback
    return token


def _preferred_size(profile, current_size):
    if current_size:
        return current_size
    if profile["size_counter"]:
        return profile["size_counter"].most_common(1)[0][0]
    if (
        profile["adventurousness_preference"]
        == User.AdventurousnessPreference.ADVENTUROUS
    ):
        return "large"
    return "medium"


def _recommended_syrups(profile, current_syrups, menu_item):
    if current_syrups:
        return list(current_syrups)[:3]

    recommended = []
    dietary_preferences = profile["dietary_preferences"]

    preferred_rank = [
        token
        for token, _ in profile["syrup_counter"].most_common()
        if token in SYRUP_OPTIONS and token not in profile["dislikes"]
    ]
    preferred_rank.extend(
        token
        for token in profile["favorite_syrups"]
        if token not in preferred_rank and token not in profile["dislikes"]
    )
    preferred_rank.extend(
        token
        for token in menu_item["default_syrups"]
        if token not in preferred_rank and token not in profile["dislikes"]
    )

    target_count = (
        2
        if profile["adventurousness_preference"]
        == User.AdventurousnessPreference.ADVENTUROUS
        else 1
    )
    for token in preferred_rank:
        if token not in SYRUP_OPTIONS:
            continue
        if not _option_allowed(SYRUP_OPTIONS[token], dietary_preferences):
            continue
        recommended.append(token)
        if len(recommended) >= target_count:
            break

    if not recommended:
        recommended = list(menu_item["default_syrups"])
    return recommended[:3]


def _recommended_add_ins(profile, current_add_ins, menu_item, chosen_soda):
    if current_add_ins:
        return list(current_add_ins)[:2]

    dietary_preferences = profile["dietary_preferences"]
    candidates = [
        token
        for token, _ in profile["add_in_counter"].most_common()
        if token in ADD_IN_OPTIONS and token not in profile["dislikes"]
    ]
    candidates.extend(
        token
        for token in profile["favorite_add_ins"]
        if token not in candidates and token not in profile["dislikes"]
    )
    candidates.extend(
        token
        for token in menu_item["default_add_ins"]
        if token not in candidates and token not in profile["dislikes"]
    )

    if "citrus" in SODA_OPTIONS[chosen_soda]["tags"]:
        for token in ("fresh-mint", "coconut-cream", "lime-wedge"):
            if token not in candidates:
                candidates.append(token)
    if "cola" in SODA_OPTIONS[chosen_soda]["tags"]:
        for token in ("lime-wedge", "cream"):
            if token not in candidates:
                candidates.append(token)

    recommended = []
    for token in candidates:
        option = ADD_IN_OPTIONS.get(token)
        if not option or not _option_allowed(option, dietary_preferences):
            continue
        recommended.append(token)
        if len(recommended) >= 2:
            break

    return recommended


def _recommended_ice_cream(profile, current_ice_cream, menu_item):
    if current_ice_cream:
        return current_ice_cream
    if "dairy-free" in profile["dietary_preferences"]:
        return ""

    if profile["favorite_ice_creams"]:
        ranked = [
            token
            for token, _ in profile["ice_cream_counter"].most_common()
            if token in profile["favorite_ice_creams"]
        ]
        if ranked:
            return ranked[0]
        return sorted(profile["favorite_ice_creams"])[0]

    if menu_item.get("default_ice_cream") and (
        "float" in menu_item["tags"]
        or profile["adventurousness_preference"]
        == User.AdventurousnessPreference.ADVENTUROUS
    ):
        return menu_item["default_ice_cream"]

    return ""


def recommend_builder_configuration(*, user, menu_item, current_selection=None):
    profile = build_user_taste_profile(user)
    current_selection = current_selection or {}
    current_syrups = list(current_selection.get("syrups") or [])
    current_add_ins = list(current_selection.get("add_ins") or [])

    size = _preferred_size(profile, current_selection.get("size"))
    soda = current_selection.get("soda") or _pick_best(
        SODA_OPTIONS.keys(),
        SODA_OPTIONS,
        profile["favorite_sodas"],
        profile["soda_counter"],
        profile["dietary_preferences"],
        fallback=menu_item["default_soda"],
    )
    if soda not in SODA_OPTIONS:
        soda = menu_item["default_soda"]

    syrups = _recommended_syrups(profile, current_syrups, menu_item)
    add_ins = _recommended_add_ins(profile, current_add_ins, menu_item, soda)
    ice_cream = _recommended_ice_cream(
        profile,
        current_selection.get("ice_cream", ""),
        menu_item,
    )

    reasons = []
    if profile["favorite_sodas"] and soda in profile["favorite_sodas"]:
        reasons.append(
            f"Picked {SODA_OPTIONS[soda]['label']} because it matches your saved favorite sodas."
        )
    elif profile["soda_counter"][soda]:
        reasons.append(
            f"Picked {SODA_OPTIONS[soda]['label']} because you have ordered similar bases before."
        )
    else:
        reasons.append(
            f"Started with {SODA_OPTIONS[soda]['label']} because it fits this signature drink well."
        )

    if syrups:
        reasons.append(
            f"Layered in {', '.join(SYRUP_OPTIONS[token]['label'] for token in syrups)} to match your preference profile and recent drinks."
        )
    if add_ins:
        reasons.append(
            f"Added {', '.join(ADD_IN_OPTIONS[token]['label'] for token in add_ins)} to round out the texture and finish."
        )
    if ice_cream:
        reasons.append(
            f"Added {ICE_CREAM_OPTIONS[ice_cream]['label']} ice cream because this build leans nicely into float territory."
        )

    return {
        "size": size,
        "soda": soda,
        "syrups": syrups[:3],
        "add_ins": add_ins[:2],
        "ice_cream": ice_cream,
        "reasons": reasons,
        "profile": profile,
    }


def recommend_drink_menu_scores(user):
    profile = build_user_taste_profile(user)
    recommendations = []
    for slug, item in MENU_ITEMS.items():
        score = 1
        reasons = []

        if slug in profile["favorite_recipe_keys"]:
            score += 6
            reasons.append("You have favorited a similar drink before.")

        if item["default_soda"] in profile["favorite_sodas"]:
            score += 4
            reasons.append("The base soda matches one of your favorites.")

        syrup_overlap = set(item["default_syrups"]) & profile["favorite_syrups"]
        if syrup_overlap:
            score += 3 * len(syrup_overlap)
            reasons.append(
                f"It lines up with flavors like {', '.join(sorted(syrup_overlap)[:2]).replace('-', ' ')}."
            )

        add_in_overlap = set(item["default_add_ins"]) & profile["favorite_add_ins"]
        if add_in_overlap:
            score += 2 * len(add_in_overlap)
            reasons.append("Its finish matches your preferred add-ins.")

        if (
            item.get("default_ice_cream")
            and item["default_ice_cream"] in profile["favorite_ice_creams"]
        ):
            score += 2
            reasons.append("Its float topper matches your saved ice cream picks.")

        item_tokens = (
            set(item["default_syrups"])
            | set(item["default_add_ins"])
            | {item["default_soda"], item.get("default_ice_cream", "")}
        )
        dislike_overlap = item_tokens & profile["dislikes"]
        if dislike_overlap:
            score -= 5 * len(dislike_overlap)
            reasons.append("It overlaps with ingredients you said to avoid.")

        if not reasons:
            reasons.append("Balanced signature build with wide demo appeal.")

        recommendations.append(
            {
                "slug": slug,
                "name": item["name"],
                "description": item["description"],
                "score": score,
                "explanation": " ".join(reasons),
                "tags": item["tags"],
            }
        )

    recommendations.sort(key=lambda row: (-row["score"], row["name"]))
    return recommendations

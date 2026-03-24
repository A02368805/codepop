from __future__ import annotations

from apps.users.models import User

from .catalog import ADD_IN_OPTIONS, ICE_CREAM_OPTIONS, SODA_OPTIONS, SYRUP_OPTIONS, ingredient_label
from .personalization import build_user_taste_profile, recommend_builder_configuration


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
    selected_syrups = [SYRUP_OPTIONS[token]["label"] for token in syrups if token in SYRUP_OPTIONS]
    selected_add_ins = [ADD_IN_OPTIONS[token]["label"] for token in add_ins if token in ADD_IN_OPTIONS]
    selected_ice_cream = ICE_CREAM_OPTIONS[ice_cream]["label"] if ice_cream in ICE_CREAM_OPTIONS else ""

    if ai_applied and ai_reasons:
        summary = "FloatStack AI filled the builder with a recommendation you can still edit freely."
        tips = list(ai_reasons)
    elif selected_ice_cream:
        summary = f"This build leans into float territory with {selected_soda_label} and {selected_ice_cream.lower()} ice cream."
        tips = ["You can still lighten the cup by swapping to a zero-sugar or citrus base."]
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
            tips.append("Your dairy-free preference is active, so creamy dairy add-ins stay out of AI suggestions.")
        elif profile["favorite_add_ins"] and not selected_add_ins:
            next_add_in = sorted(profile["favorite_add_ins"])[0]
            tips.append(f"You often lean toward {ingredient_label(next_add_in)} in saved preferences.")

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
        "uses_preferences": bool(
            _authenticated_preferences(user)
        ),
    }


def _authenticated_preferences(user):
    return bool(
        getattr(user, "is_authenticated", False)
        and getattr(user, "role", None) == User.Role.ACCOUNT_USER
        and user.taste_preferences.exists()
    )

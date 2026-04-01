from __future__ import annotations

import json
import logging
import re
import time
from urllib import error as url_error
from urllib import request as url_request

from apps.orders.models import Order
from apps.orders.selectors import user_can_view_order
from django.conf import settings
from django.urls import reverse

from .models import SupportConversation, SupportEscalation, SupportMessage

logger = logging.getLogger(__name__)

ORDER_CODE_PATTERN = re.compile(r"\bFS-[A-Z0-9-]+\b", re.IGNORECASE)
LOOKUP_CODE_PATTERN = re.compile(r"\bGST-[A-Z0-9-]+\b", re.IGNORECASE)

DEFAULT_QUICK_PROMPTS = [
    "Where is my order?",
    "Can I cancel my drink?",
    "How does guest lookup work?",
    "I need help with pickup timing",
]


def ensure_support_session(request):
    if not request.session.session_key:
        request.session.save()
    return request.session.session_key or ""


def user_can_access_conversation(request, conversation):
    user = request.user
    if getattr(user, "is_authenticated", False):
        return conversation.user_id == user.id
    session_key = ensure_support_session(request)
    return conversation.user_id is None and conversation.guest_session_key == session_key


def get_or_create_active_conversation(request):
    user = request.user
    if getattr(user, "is_authenticated", False):
        conversation = (
            SupportConversation.objects.filter(
                user=user,
                status=SupportConversation.Status.OPEN,
            )
            .select_related("linked_order", "linked_store")
            .first()
        )
        if conversation:
            return conversation
        return SupportConversation.objects.create(user=user)

    session_key = ensure_support_session(request)
    conversation = (
        SupportConversation.objects.filter(
            user__isnull=True,
            guest_session_key=session_key,
            status=SupportConversation.Status.OPEN,
        )
        .select_related("linked_order", "linked_store")
        .first()
    )
    if conversation:
        return conversation
    return SupportConversation.objects.create(guest_session_key=session_key)


def start_new_conversation(request):
    conversation = get_or_create_active_conversation(request)
    if conversation.messages.exists():
        conversation.status = SupportConversation.Status.CLOSED
        conversation.save(update_fields=["status", "updated_at"])
        conversation = get_or_create_active_conversation(request)
    SupportMessage.objects.create(
        conversation=conversation,
        role=SupportMessage.Role.ASSISTANT,
        intent="welcome",
        content=(
            "Hi, I am the CodePop support assistant. I can help with order status, "
            "guest lookup, cancellation/refund rules, pickup timing, and account navigation."
        ),
    )
    return conversation


def _extract_order_code(text):
    match = ORDER_CODE_PATTERN.search(text or "")
    return match.group(0).upper() if match else ""


def _extract_lookup_code(text):
    match = LOOKUP_CODE_PATTERN.search(text or "")
    return match.group(0).upper() if match else ""


def _resolve_order_context(conversation, request, message_text):
    order_code = _extract_order_code(message_text)
    if not order_code and conversation.linked_order_id:
        return conversation.linked_order
    if not order_code:
        return None

    order = (
        Order.objects.select_related("store", "guest_contact", "customer")
        .filter(public_order_code=order_code)
        .first()
    )
    if not order:
        return None
    if not user_can_view_order(request.user, order, session=request.session):
        return None

    conversation.linked_order = order
    conversation.linked_store = order.store
    conversation.save(update_fields=["linked_order", "linked_store", "updated_at"])
    return order


def _intent_for_message(text):
    lowered = (text or "").lower()
    if "guest" in lowered and ("lookup" in lowered or "track" in lowered):
        return "guest_lookup"
    if any(token in lowered for token in ["where", "status", "track", "order"]):
        return "order_status"
    if any(token in lowered for token in ["cancel", "refund"]):
        return "refund_policy"
    if any(token in lowered for token in ["favorite", "history", "preference", "account"]):
        return "account_help"
    if any(token in lowered for token in ["store", "pickup", "timing", "wait"]):
        return "store_pickup_help"
    if any(token in lowered for token in ["build", "drink", "recommend", "flavor"]):
        return "drink_builder_help"
    if any(token in lowered for token in ["issue", "problem", "complaint", "wrong"]):
        return "escalation_help"
    return "general_help"


def _intent_response(*, intent, request, conversation, message_text, order):
    quick_actions = []
    links = []
    suggest_escalation = False

    if intent == "order_status":
        if order:
            reply = (
                f"Your order {order.public_order_code} is currently {order.get_status_display().lower()}. "
                f"Pickup store: {order.store.name}."
            )
            if order.pickup_time_requested:
                reply += " I recommend arriving near your requested pickup time so freshness stays high."
            links.append({"label": "Open order details", "url": reverse("orders:detail", args=[order.public_order_code])})
        else:
            reply = (
                "I can help track an order if you share its public code (for example FS-C-C001-XXXXXX). "
                "For guest orders, you can also use the guest lookup flow."
            )
            links.append({"label": "Guest order lookup", "url": reverse("orders:guest-lookup")})
        quick_actions = ["How do I track a guest order?", "Can I cancel my drink?"]
    elif intent == "refund_policy":
        if order and order.status in {Order.Status.PAID, Order.Status.QUEUED, Order.Status.PAYMENT_PENDING}:
            reply = (
                "Based on the current order state, cancellation/refund is generally allowed before preparation begins. "
                "Use the order details page to continue through the existing cancellation flow."
            )
            links.append({"label": "Open order details", "url": reverse("orders:detail", args=[order.public_order_code])})
        elif order and order.status in {Order.Status.PREPARING, Order.Status.READY, Order.Status.PICKED_UP}:
            reply = (
                "Refund eligibility normally ends once preparation begins. "
                "If you had a product issue, I can open a support escalation for human follow-up."
            )
            suggest_escalation = True
        else:
            reply = (
                "CodePop policy is that refund eligibility ends when preparation begins. "
                "Before that point, cancellation can be handled from the order details workflow."
            )
        quick_actions = ["Where is my order?", "I had an issue with my drink"]
    elif intent == "guest_lookup":
        lookup_code = _extract_lookup_code(message_text)
        reply = (
            "Guest orders are tracked through the guest lookup page using the checkout lookup code. "
            "Guest users are not persisted as full account users."
        )
        if lookup_code:
            reply += f" You can paste {lookup_code} on the guest lookup page now."
        links.append({"label": "Open guest lookup", "url": reverse("orders:guest-lookup")})
        quick_actions = ["Where is my order?", "How do favorites work?"]
    elif intent == "account_help":
        if getattr(request.user, "is_authenticated", False):
            reply = (
                "From your customer dashboard you can manage favorites, taste preferences, "
                "and account order history without changing staff workflows."
            )
            links.extend(
                [
                    {"label": "Customer dashboard", "url": reverse("customer-dashboard")},
                    {"label": "Favorites", "url": reverse("orders:favorites")},
                    {"label": "Order history", "url": reverse("orders:history")},
                ]
            )
        else:
            reply = (
                "Favorites and account history are available to account users after sign-in. "
                "Guest checkout still works without creating a persistent user profile."
            )
            links.append({"label": "Sign in", "url": reverse("login")})
        quick_actions = ["Can you help me build a drink?", "How do I choose the best store?"]
    elif intent == "store_pickup_help":
        reply = (
            "Store selection and pickup timing are advisory choices you control before checkout. "
            "A good default is the nearest open store with your preferred pickup window."
        )
        links.extend(
            [
                {"label": "Find stores", "url": reverse("stores:index")},
                {"label": "Browse menu", "url": reverse("orders:index")},
            ]
        )
        quick_actions = ["Where is my order?", "Can I cancel my drink?"]
    elif intent == "drink_builder_help":
        reply = (
            "I can guide your drink builder choices with suggestions, but all final edits stay in your control. "
            "Use the AI builder helper on a store menu item to refine soda, syrups, and add-ins."
        )
        links.append({"label": "Start with stores", "url": reverse("stores:index")})
        quick_actions = ["Can you help me build a drink?", "How do favorites work?"]
    elif intent == "escalation_help":
        reply = (
            "I am sorry this did not go smoothly. I can capture a support escalation with your summary "
            "so the team can follow up."
        )
        suggest_escalation = True
        quick_actions = ["I had an issue with my drink", "Still need help"]
    else:
        reply = (
            "I can help with order tracking, guest lookup, cancellation/refund policy, "
            "store and pickup guidance, drink builder help, and account navigation."
        )
        quick_actions = list(DEFAULT_QUICK_PROMPTS)

    return {
        "reply_text": reply,
        "quick_actions": [{"label": text, "prompt": text} for text in quick_actions[:4]],
        "links": links,
        "suggest_escalation": suggest_escalation,
    }


def _call_anthropic_support_ai(*, request, conversation, message_text, order, deterministic_response):
    api_key = str(getattr(settings, "ANTHROPIC_API_KEY", "") or "").strip()
    if not api_key:
        return None

    base_url = str(
        getattr(settings, "ANTHROPIC_API_BASE_URL", "https://api.anthropic.com")
    ).rstrip("/")
    model = str(getattr(settings, "ANTHROPIC_MODEL", "claude-3-5-haiku-latest"))
    timeout_seconds = float(getattr(settings, "AI_PROVIDER_TIMEOUT_SECONDS", 8))
    max_retries = int(getattr(settings, "AI_PROVIDER_MAX_RETRIES", 2))

    system_prompt = (
        "You are the CodePop support assistant. Use the supplied policy context to write a short, helpful reply. "
        "Do not change the policy facts, links, escalation guidance, or order status. "
        "Return JSON only with this exact shape: {\"reply_text\": string}. "
        "Keep the reply under 120 words and do not mention that you are an AI model."
    )
    body = {
        "model": model,
        "max_tokens": 220,
        "messages": [
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "message": message_text,
                        "conversation": {
                            "id": str(conversation.id),
                            "status": conversation.status,
                            "intent": deterministic_response.get("intent", "general_help"),
                        },
                        "order": {
                            "public_order_code": getattr(order, "public_order_code", ""),
                            "status": getattr(order, "status", ""),
                            "store_name": getattr(getattr(order, "store", None), "name", ""),
                        }
                        if order
                        else None,
                        "deterministic_context": {
                            "reply_text": deterministic_response.get("reply_text", ""),
                            "quick_actions": deterministic_response.get("quick_actions", []),
                            "links": deterministic_response.get("links", []),
                            "suggest_escalation": deterministic_response.get("suggest_escalation", False),
                        },
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
            reply_text = str(parsed.get("reply_text", "")).strip()
            if not reply_text:
                raise ValueError("Anthropic support response did not include reply_text.")
            return {"reply_text": reply_text}
        except (ValueError, json.JSONDecodeError, TimeoutError, url_error.URLError, url_error.HTTPError) as exc:
            logger.warning(
                "support_ai_provider_attempt_failed",
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


def process_support_message(*, request, conversation, message_text):
    trimmed = (message_text or "").strip()
    if not trimmed:
        return {
            "reply_text": "Please send a message so I can help.",
            "quick_actions": [{"label": text, "prompt": text} for text in DEFAULT_QUICK_PROMPTS],
            "links": [],
            "suggest_escalation": False,
            "intent": "general_help",
        }

    intent = _intent_for_message(trimmed)
    order = _resolve_order_context(conversation, request, trimmed)
    response = _intent_response(
        intent=intent,
        request=request,
        conversation=conversation,
        message_text=trimmed,
        order=order,
    )
    response["intent"] = intent

    anthropic_response = _call_anthropic_support_ai(
        request=request,
        conversation=conversation,
        message_text=trimmed,
        order=order,
        deterministic_response=response,
    )
    if anthropic_response:
        response["reply_text"] = anthropic_response["reply_text"]

    SupportMessage.objects.create(
        conversation=conversation,
        role=SupportMessage.Role.USER,
        intent=intent,
        content=trimmed,
        metadata_json={},
    )
    SupportMessage.objects.create(
        conversation=conversation,
        role=SupportMessage.Role.ASSISTANT,
        intent=intent,
        content=response["reply_text"],
        metadata_json={
            "quick_actions": response["quick_actions"],
            "links": response["links"],
            "suggest_escalation": response["suggest_escalation"],
        },
    )

    conversation.last_intent = intent
    if order and not conversation.linked_store_id:
        conversation.linked_store = order.store
    conversation.save(update_fields=["last_intent", "linked_store", "updated_at"])
    return response


def create_escalation(*, conversation, request, summary, contact_email=""):
    escalation = SupportEscalation.objects.create(
        conversation=conversation,
        user=request.user if request.user.is_authenticated else None,
        linked_order=conversation.linked_order,
        linked_store=conversation.linked_store,
        contact_email=contact_email,
        summary=summary.strip(),
        status=SupportEscalation.Status.OPEN,
    )
    SupportMessage.objects.create(
        conversation=conversation,
        role=SupportMessage.Role.SYSTEM,
        intent="escalation_created",
        content="Support escalation created. A team member can follow up using your summary.",
        metadata_json={"escalation_id": str(escalation.id)},
    )
    return escalation

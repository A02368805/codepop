from __future__ import annotations

import json
import logging
import re
import ssl
import time
from urllib import error as url_error
from urllib import request as url_request

import certifi
from apps.orders.models import Order
from apps.orders.selectors import user_can_view_order
from django.conf import settings
from django.urls import reverse

from .models import SupportConversation, SupportEscalation, SupportMessage

logger = logging.getLogger(__name__)
SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())

ORDER_CODE_PATTERN = re.compile(r"\bFS-[A-Z0-9-]+\b", re.IGNORECASE)
LOOKUP_CODE_PATTERN = re.compile(r"\bGST-[A-Z0-9-]+\b", re.IGNORECASE)

DEFAULT_QUICK_PROMPTS = []
SUPPORT_SCOPE_KEYWORDS = (
    "floatstack",
    "order",
    "pickup",
    "guest",
    "lookup",
    "refund",
    "cancel",
    "account",
    "login",
    "password",
    "store",
    "menu",
    "cart",
    "checkout",
    "status",
    "code",
    "payment",
)
SUPPORT_KNOWLEDGE_BASE = {
    "what_is_floatstack": (
        "Here at FloatStack, we help customers choose a store, customize soda/float "
        "drinks, place an order, and pick it up when it is marked ready."
    ),
    "order_flow": [
        "Choose a store.",
        "Build drinks from menu signatures or custom options.",
        "Add items to cart and checkout.",
        "Track order status by public order code.",
        "Pick up at the selected store once status is ready.",
    ],
    "pickup_flow": [
        "Use the order code from confirmation or guest lookup.",
        "Wait for status to move to ready.",
        "Go to the same store selected at checkout.",
        "Show order code at pickup.",
    ],
}


def ensure_support_session(request):
    if not request.session.session_key:
        request.session.save()
    return request.session.session_key or ""


def user_can_access_conversation(request, conversation):
    user = request.user
    if getattr(user, "is_authenticated", False):
        return conversation.user_id == user.id
    session_key = ensure_support_session(request)
    return (
        conversation.user_id is None and conversation.guest_session_key == session_key
    )


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
            "Hi, I am part of the FloatStack support team. I can help with order status, "
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


def _recent_conversation_messages(conversation, *, limit=10):
    rows = conversation.messages.order_by("-created_at").values("role", "content")[
        :limit
    ]
    return list(reversed(rows))


def _build_support_context(*, request, conversation, order):
    user = request.user
    user_role = (
        getattr(user, "role", "guest")
        if getattr(user, "is_authenticated", False)
        else "guest"
    )
    context = {
        "conversation_id": str(conversation.id),
        "user_role": user_role,
        "history": _recent_conversation_messages(conversation),
        "known_order": None,
    }
    if order:
        context["known_order"] = {
            "public_order_code": order.public_order_code,
            "status": order.status,
            "status_display": order.get_status_display(),
            "store_name": order.store.name,
            "pickup_time_requested": (
                order.pickup_time_requested.isoformat()
                if order.pickup_time_requested
                else ""
            ),
        }
    context["knowledge_base"] = SUPPORT_KNOWLEDGE_BASE
    return context


def _is_support_scope_message(message_text):
    lowered = (message_text or "").lower()
    return any(keyword in lowered for keyword in SUPPORT_SCOPE_KEYWORDS)


def _call_anthropic_support_ai(*, request, conversation, message_text, order):
    api_key = str(getattr(settings, "ANTHROPIC_API_KEY", "") or "").strip()
    if not api_key:
        logger.info("support_ai_skipped_missing_api_key")
        return None

    base_url = str(
        getattr(settings, "ANTHROPIC_API_BASE_URL", "https://api.anthropic.com")
    ).rstrip("/")
    model = str(getattr(settings, "ANTHROPIC_MODEL", "claude-3-5-haiku-latest"))
    timeout_seconds = float(getattr(settings, "AI_PROVIDER_TIMEOUT_SECONDS", 8))
    max_retries = int(getattr(settings, "AI_PROVIDER_MAX_RETRIES", 2))

    system_prompt = (
        "You are the FloatStack support assistant and part of the FloatStack team. "
        "Use first-person team voice (we/us/our at FloatStack) instead of detached third-person phrasing. "
        "Respond conversationally and helpfully. "
        "You are strictly scoped to FloatStack support topics: what FloatStack is, order flow, pickup, guest lookup, refunds/cancellations, and account navigation. "
        "If a question is outside FloatStack support scope, politely refuse and redirect to support topics. "
        "If order details are missing, ask for the public order code. "
        "Never invent order status, refunds, or pricing details. "
        "Keep replies under 140 words and provide only plain response text."
    )
    support_context = _build_support_context(
        request=request,
        conversation=conversation,
        order=order,
    )
    body = {
        "model": model,
        "max_tokens": 260,
        "messages": [
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "message": message_text,
                        "support_context": support_context,
                        "available_links": {
                            "guest_lookup": reverse("orders:guest-lookup"),
                            "stores": reverse("stores:index"),
                            "orders_history": (
                                reverse("orders:history")
                                if getattr(request.user, "is_authenticated", False)
                                else ""
                            ),
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
            with url_request.urlopen(
                req,
                timeout=timeout_seconds,
                context=SSL_CONTEXT,
            ) as resp:
                payload = json.loads(resp.read().decode("utf-8"))

            text_block = ""
            for block in payload.get("content") or []:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_block = block.get("text", "")
                    break
            if not text_block:
                raise ValueError("Anthropic response did not contain text content.")

            reply_text = str(text_block).strip()
            if not reply_text:
                raise ValueError("Anthropic support response did not include text.")
            links = []
            if order:
                links.append(
                    {
                        "label": "Open order details",
                        "url": reverse("orders:detail", args=[order.public_order_code]),
                    }
                )
            else:
                links.append(
                    {"label": "Guest lookup", "url": reverse("orders:guest-lookup")}
                )
            return {
                "reply_text": reply_text,
                "suggest_escalation": False,
                "links": links,
            }
        except (
            ValueError,
            json.JSONDecodeError,
            TimeoutError,
            url_error.URLError,
            url_error.HTTPError,
        ) as exc:
            logger.warning(
                "support_ai_provider_attempt_failed type=%s detail=%s",
                exc.__class__.__name__,
                str(exc),
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


def _fallback_general_support_info(message_text):
    lowered = (message_text or "").lower()
    if "what is floatstack" in lowered or "about floatstack" in lowered:
        return (
            "Here at FloatStack, we run a soda and float ordering experience: you choose a store, "
            "build drinks, checkout, and track your order by public order code until pickup."
        )
    if "order flow" in lowered or "how do i order" in lowered:
        return (
            "Our order flow is: choose a store, build drinks, add to cart, checkout, then "
            "track status by public order code until pickup."
        )
    if "pickup" in lowered:
        return (
            "For pickup with us, use the same store selected at checkout, wait for ready status, "
            "and show your public order code at pickup."
        )
    return ""


def _fallback_support_reply(*, order, message_text):
    lowered = (message_text or "").lower()
    links = []
    suggest_escalation = any(
        word in lowered for word in ["issue", "wrong", "problem", "refund"]
    )
    if order:
        reply = (
            f"I found order {order.public_order_code}. It is currently {order.get_status_display().lower()} at {order.store.name}. "
            "If you want, I can also help with pickup timing or cancellation guidance."
        )
        links.append(
            {
                "label": "Open order details",
                "url": reverse("orders:detail", args=[order.public_order_code]),
            }
        )
    else:
        scope_reply = _fallback_general_support_info(message_text)
        if scope_reply:
            reply = scope_reply
        elif not _is_support_scope_message(message_text):
            reply = (
                "I can only help with FloatStack support topics like order flow, pickup, "
                "guest lookup, refunds, and account questions."
            )
        else:
            reply = (
                "I can help with order status, refunds, pickup timing, and account questions. "
                "If this is about a specific order, share your public order code so I can ground the response."
            )
        links.append({"label": "Guest lookup", "url": reverse("orders:guest-lookup")})
        links.append({"label": "Browse stores", "url": reverse("stores:index")})
    return {
        "reply_text": reply,
        "links": links,
        "suggest_escalation": suggest_escalation,
    }


def process_support_message(*, request, conversation, message_text):
    trimmed = (message_text or "").strip()
    if not trimmed:
        return {
            "reply_text": "Please send a message so I can help.",
            "quick_actions": [
                {"label": text, "prompt": text} for text in DEFAULT_QUICK_PROMPTS
            ],
            "links": [],
            "suggest_escalation": False,
            "intent": "chat",
        }

    intent = "chat"
    order = _resolve_order_context(conversation, request, trimmed)
    anthropic_response = None
    if _is_support_scope_message(trimmed):
        anthropic_response = _call_anthropic_support_ai(
            request=request,
            conversation=conversation,
            message_text=trimmed,
            order=order,
        )
    response = anthropic_response or _fallback_support_reply(
        order=order,
        message_text=trimmed,
    )
    response["quick_actions"] = []
    response["intent"] = intent

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

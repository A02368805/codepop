from apps.support.models import SupportConversation
from apps.users.permissions import user_can_use_customer_ordering
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.views import View
from django.views.generic import TemplateView

from .forms import SupportEscalationForm, SupportMessageForm
from .services import (
    create_escalation,
    get_or_create_active_conversation,
    process_support_message,
    start_new_conversation,
    user_can_access_conversation,
)


class CustomerSupportAccessMixin:
    permission_denied_message = (
        "Customer support is only available for guests and customer accounts."
    )

    def dispatch(self, request, *args, **kwargs):
        if not user_can_use_customer_ordering(request.user):
            raise PermissionDenied(self.permission_denied_message)
        return super().dispatch(request, *args, **kwargs)


def _workspace_context(
    request,
    conversation,
    *,
    message_form=None,
    escalation_form=None,
):
    messages_qs = conversation.messages.order_by("created_at")
    last_assistant_message = (
        messages_qs.filter(role="assistant").order_by("-created_at").first()
    )
    latest_meta = getattr(last_assistant_message, "metadata_json", {}) or {}

    if message_form is None:
        message_form = SupportMessageForm()
    if escalation_form is None:
        escalation_form = SupportEscalationForm(
            initial={
                "summary": (
                    f"Need follow-up for support conversation {conversation.id}. "
                    f"Last intent: {conversation.last_intent or 'general_help'}."
                )
            }
        )

    return {
        "conversation": conversation,
        "thread_messages": messages_qs,
        "message_form": message_form,
        "escalation_form": escalation_form,
        "quick_actions": latest_meta.get("quick_actions", []),
        "related_links": latest_meta.get("links", []),
        "show_escalation": bool(latest_meta.get("suggest_escalation")),
    }


def _render_workspace(request, conversation, **context_overrides):
    return render_to_string(
        "support/partials/workspace.html",
        _workspace_context(request, conversation, **context_overrides),
        request=request,
    )


class SupportHomeView(CustomerSupportAccessMixin, TemplateView):
    template_name = "support/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        conversation = get_or_create_active_conversation(self.request)
        if not conversation.messages.exists():
            conversation = start_new_conversation(self.request)
        context.update(_workspace_context(self.request, conversation))
        return context


class SupportConversationDetailView(CustomerSupportAccessMixin, TemplateView):
    template_name = "support/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        conversation = get_object_or_404(
            SupportConversation, pk=kwargs["conversation_id"]
        )
        if not user_can_access_conversation(self.request, conversation):
            raise PermissionDenied("You don't have access to this conversation.")
        context.update(_workspace_context(self.request, conversation))
        return context


class SupportStartView(CustomerSupportAccessMixin, View):
    def post(self, request, *args, **kwargs):
        conversation = start_new_conversation(request)
        html = _render_workspace(request, conversation)
        return HttpResponse(html)


class SupportSendView(CustomerSupportAccessMixin, View):
    def post(self, request, *args, **kwargs):
        conversation = get_object_or_404(
            SupportConversation, pk=kwargs["conversation_id"]
        )
        if not user_can_access_conversation(request, conversation):
            raise PermissionDenied("You don't have access to this conversation.")

        form = SupportMessageForm(request.POST)
        if form.is_valid():
            process_support_message(
                request=request,
                conversation=conversation,
                message_text=form.cleaned_data["message"],
            )
            html = _render_workspace(request, conversation)
        else:
            html = _render_workspace(request, conversation, message_form=form)
        return HttpResponse(html)


class SupportEscalateView(CustomerSupportAccessMixin, View):
    def post(self, request, *args, **kwargs):
        conversation = get_object_or_404(
            SupportConversation, pk=kwargs["conversation_id"]
        )
        if not user_can_access_conversation(request, conversation):
            raise PermissionDenied("You don't have access to this conversation.")

        form = SupportEscalationForm(request.POST)
        if form.is_valid():
            create_escalation(
                conversation=conversation,
                request=request,
                summary=form.cleaned_data["summary"],
                contact_email=form.cleaned_data["contact_email"],
            )
            messages.success(
                request,
                "Support escalation submitted. A follow-up can be handled by the team.",
            )
            html = _render_workspace(request, conversation)
        else:
            html = _render_workspace(request, conversation, escalation_form=form)
        return HttpResponse(html)

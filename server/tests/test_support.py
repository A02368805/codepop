from decimal import Decimal
from unittest.mock import patch

from apps.orders.models import Order
from apps.orders.services import create_order, transition_order_status
from apps.payments.models import PaymentTransaction
from apps.payments.services import record_payment_pending, record_payment_success
from apps.support.models import SupportConversation, SupportEscalation, SupportMessage
from apps.support.services import process_support_message
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import Client, TestCase
from django.test.client import RequestFactory
from django.urls import reverse

from .helpers import assign_store, make_region, make_store, make_user


class SupportFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.region = make_region(code="C", name="Logan, UT")
        cls.store = make_store(store_code="C001", region=cls.region, name="Logan Main")
        cls.customer = make_user(
            email="support-customer@test.local",
            preferred_store=cls.store,
            default_region=cls.region,
        )
        cls.manager = make_user(
            email="support-manager@test.local",
            role="manager",
            preferred_store=cls.store,
            default_region=cls.region,
        )
        assign_store(cls.manager, cls.store)

    def test_guest_conversation_flow_creates_messages(self):
        guest_client = Client()

        response = guest_client.get(reverse("support:index"))
        self.assertEqual(response.status_code, 200)
        conversation = SupportConversation.objects.get(user__isnull=True)
        self.assertTrue(conversation.guest_session_key)
        self.assertTrue(
            SupportMessage.objects.filter(
                conversation=conversation,
                role=SupportMessage.Role.ASSISTANT,
                intent="welcome",
            ).exists()
        )

        response = guest_client.post(
            reverse("support:send", args=[conversation.id]),
            {"message": "How do I track a guest order?"},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "guest lookup")
        self.assertEqual(conversation.messages.filter(role="user").count(), 1)

    def test_account_user_support_flow_works(self):
        self.client.force_login(self.customer)

        response = self.client.get(reverse("support:index"))
        self.assertEqual(response.status_code, 200)
        conversation = SupportConversation.objects.get(user=self.customer)

        response = self.client.post(
            reverse("support:send", args=[conversation.id]),
            {"message": "How do favorites work?"},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "favorites")
        self.assertTrue(
            conversation.messages.filter(role=SupportMessage.Role.ASSISTANT).exists()
        )

    def test_staff_user_is_blocked_from_customer_support(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse("support:index"))
        self.assertEqual(response.status_code, 403)

    def test_escalation_creation_links_context(self):
        self.client.force_login(self.customer)
        self.client.get(reverse("support:index"))
        conversation = SupportConversation.objects.get(user=self.customer)

        response = self.client.post(
            reverse("support:escalate", args=[conversation.id]),
            {
                "summary": "I had an issue with drink quality and need follow-up.",
                "contact_email": "support-followup@test.local",
            },
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)

        escalation = SupportEscalation.objects.get(conversation=conversation)
        self.assertEqual(escalation.status, SupportEscalation.Status.OPEN)
        self.assertEqual(escalation.contact_email, "support-followup@test.local")
        self.assertContains(response, "Support escalation")

    def test_order_linked_help_and_no_mutation(self):
        order = create_order(
            store=self.store,
            customer=self.customer,
            items=[
                {
                    "display_name": "Berry Burst",
                    "size": "medium",
                    "base_price": Decimal("5.50"),
                    "extras_total": Decimal("0.50"),
                    "quantity": 1,
                    "customizations": {
                        "extras_total": "0.50",
                        "inventory_requirements": [],
                    },
                }
            ],
            actor=self.customer,
        )
        record_payment_pending(order, payment_intent_id="pi_support_order")
        record_payment_success(
            order, payment_intent_id="pi_support_order", actor=self.customer
        )
        transition_order_status(order, Order.Status.QUEUED, actor=self.customer)

        self.client.force_login(self.customer)
        self.client.get(reverse("support:index"))
        conversation = SupportConversation.objects.get(user=self.customer)

        response = self.client.post(
            reverse("support:send", args=[conversation.id]),
            {"message": f"Can I cancel order {order.public_order_code}?"},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, order.public_order_code)

        order.refresh_from_db()
        payment = PaymentTransaction.objects.get(order=order)
        self.assertEqual(order.status, Order.Status.QUEUED)
        self.assertEqual(payment.status, PaymentTransaction.Status.SUCCEEDED)


class SupportAssistantServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.region = make_region(code="C", name="Logan, UT")
        cls.store = make_store(store_code="C001", region=cls.region, name="Logan Main")
        cls.customer = make_user(
            email="support-service@test.local",
            preferred_store=cls.store,
            default_region=cls.region,
        )

    @patch("apps.support.services._call_anthropic_support_ai")
    def test_support_chat_uses_api_response(self, mock_ai_call):
        mock_ai_call.return_value = {
            "reply_text": "I can help with that. Please share your order code so I can check status.",
            "links": [{"label": "Guest lookup", "url": reverse("orders:guest-lookup")}],
            "suggest_escalation": False,
        }

        conversation = SupportConversation.objects.create(user=self.customer)
        factory = RequestFactory()

        request = factory.get("/")
        middleware = SessionMiddleware(lambda req: None)
        middleware.process_request(request)
        request.session.save()
        request.user = self.customer
        response = process_support_message(
            request=request,
            conversation=conversation,
            message_text="Where is my order?",
        )

        self.assertIn("please share your order code", response["reply_text"].lower())
        self.assertEqual(response["intent"], "chat")
        self.assertEqual(len(response["links"]), 1)
        mock_ai_call.assert_called_once()

    @patch("apps.support.services._call_anthropic_support_ai")
    def test_support_chat_fallback_when_api_unavailable(self, mock_ai_call):
        mock_ai_call.return_value = None
        conversation = SupportConversation.objects.create(user=self.customer)
        factory = RequestFactory()

        request = factory.get("/")
        middleware = SessionMiddleware(lambda req: None)
        middleware.process_request(request)
        request.session.save()
        request.user = self.customer
        response = process_support_message(
            request=request,
            conversation=conversation,
            message_text="I need help with my order",
        )

        self.assertIn("public order code", response["reply_text"].lower())
        self.assertEqual(response["intent"], "chat")

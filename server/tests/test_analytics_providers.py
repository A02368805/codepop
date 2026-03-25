from unittest.mock import patch
from urllib import error as url_error

from apps.analytics.recommendations import recommend_drinks_for_user
from django.test import TestCase, override_settings

from .helpers import make_region, make_store, make_user


class AnalyticsProviderSelectionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.region = make_region(code="C", name="Logan, UT")
        cls.store = make_store(store_code="C001", region=cls.region, name="Logan Main")
        cls.customer = make_user(
            email="ai-provider@test.local",
            preferred_store=cls.store,
            default_region=cls.region,
        )

    @override_settings(AI_RECOMMENDATION_PROVIDER="deterministic")
    def test_deterministic_provider_returns_recommendations(self):
        rows = recommend_drinks_for_user(self.customer, limit=2)
        self.assertGreaterEqual(len(rows), 1)
        self.assertIn("name", rows[0])
        self.assertIn("explanation", rows[0])

    @override_settings(AI_RECOMMENDATION_PROVIDER="mock-external")
    def test_mock_external_provider_marks_explanations(self):
        rows = recommend_drinks_for_user(self.customer, limit=2)
        self.assertGreaterEqual(len(rows), 1)
        self.assertIn("[Mock external provider]", rows[0]["explanation"])

    @override_settings(AI_RECOMMENDATION_PROVIDER="not-a-provider")
    def test_unknown_provider_falls_back_to_deterministic(self):
        rows = recommend_drinks_for_user(self.customer, limit=2)
        self.assertGreaterEqual(len(rows), 1)
        self.assertNotIn("[Mock external provider]", rows[0]["explanation"])

    @override_settings(
        AI_RECOMMENDATION_PROVIDER="anthropic",
        ANTHROPIC_API_KEY="test-key",
        AI_PROVIDER_MAX_RETRIES=0,
    )
    @patch("apps.analytics.providers.url_request.urlopen")
    def test_anthropic_provider_uses_response_payload(self, mock_urlopen):
        class _Resp:
            def __enter__(self_inner):
                return self_inner

            def __exit__(self_inner, exc_type, exc, tb):
                return False

            def read(self_inner):
                return b'{"content":[{"type":"text","text":"{\\"recommendations\\":[{\\"name\\":\\"Berry Burst\\",\\"explanation\\":\\"AI tuned for bright citrus balance.\\"}]}"}]}'

        mock_urlopen.return_value = _Resp()
        rows = recommend_drinks_for_user(self.customer, limit=2)
        self.assertGreaterEqual(len(rows), 1)
        target = next((row for row in rows if row["name"] == "Berry Burst"), rows[0])
        self.assertIn("AI tuned", target["explanation"])

    @override_settings(
        AI_RECOMMENDATION_PROVIDER="anthropic",
        ANTHROPIC_API_KEY="test-key",
        AI_PROVIDER_MAX_RETRIES=0,
    )
    @patch("apps.analytics.providers.url_request.urlopen")
    def test_anthropic_provider_falls_back_to_deterministic_on_error(
        self, mock_urlopen
    ):
        mock_urlopen.side_effect = url_error.URLError("timeout")
        rows = recommend_drinks_for_user(self.customer, limit=2)
        self.assertGreaterEqual(len(rows), 1)
        self.assertNotIn("[Mock external provider]", rows[0]["explanation"])

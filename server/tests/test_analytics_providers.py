from django.test import TestCase, override_settings

from apps.analytics.recommendations import recommend_drinks_for_user

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

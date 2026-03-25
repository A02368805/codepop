from apps.users.models import UserStoreAssignment
from django.test import TestCase
from django.urls import reverse

from .helpers import assign_store, make_region, make_store, make_user


class ScaffoldSmokeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.region = make_region(code="C", name="Logan, UT")
        cls.store = make_store(
            store_code="C001", region=cls.region, name="Provo Flagship"
        )
        cls.customer = make_user(
            email="customer@test.local",
            preferred_store=cls.store,
            default_region=cls.region,
        )
        cls.manager = make_user(
            email="manager@test.local",
            role="manager",
            preferred_store=cls.store,
            default_region=cls.region,
        )
        assign_store(
            cls.manager,
            cls.store,
            assignment_type=UserStoreAssignment.AssignmentType.MANAGER_SCOPE,
        )

    def test_homepage_loads_for_anonymous_users(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "FloatStack")
        self.assertContains(response, "Build a drink")

    def test_dashboard_redirects_to_role_specific_page(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse("dashboard"))
        self.assertRedirects(response, reverse("manager-dashboard"))

    def test_customer_cannot_open_manager_dashboard(self):
        self.client.force_login(self.customer)
        response = self.client.get(reverse("manager-dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_dashboard_metrics_partial_renders(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse("analytics:dashboard-metrics"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Live Summary")

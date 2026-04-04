from apps.analytics.recommendations import recommend_drinks_for_user
from apps.orders.catalog import MENU_ITEMS, SODA_OPTIONS
from django.test import TestCase
from django.urls import reverse

from .models import TastePreference, User


class PreferenceRecommendationFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="preference.test@floatstack.local",
            password="FloatStack123!",
            role=User.Role.ACCOUNT_USER,
            status=User.Status.ACTIVE,
        )
        self.client.force_login(self.user)

    def test_account_preferences_post_persists_selected_profile(self):
        response = self.client.post(
            reverse("account-preferences"),
            data={
                "favorite_sodas": ["sprite"],
                "favorite_syrups": ["lime"],
                "favorite_add_ins": ["fresh-mint"],
                "favorite_ice_creams": [],
                "disliked_ingredients": ["coke"],
                "dietary_preferences": ["caffeine-free"],
                "sweetness_preference": User.SweetnessPreference.LIGHT,
                "adventurousness_preference": User.AdventurousnessPreference.CLASSIC,
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)

        preferences = set(
            TastePreference.objects.filter(user=self.user).values_list(
                "preference_type", "ingredient_name"
            )
        )
        self.assertIn(
            (TastePreference.PreferenceType.FAVORITE_SODA, "sprite"), preferences
        )
        self.assertIn(
            (TastePreference.PreferenceType.FAVORITE_SYRUP, "lime"), preferences
        )
        self.assertIn(
            (TastePreference.PreferenceType.FAVORITE_ADD_IN, "fresh-mint"), preferences
        )
        self.assertIn((TastePreference.PreferenceType.DISLIKE, "coke"), preferences)
        self.assertIn(
            (TastePreference.PreferenceType.DIETARY, "caffeine-free"), preferences
        )

    def test_recommendations_respect_saved_preferences_and_constraints(self):
        self.client.post(
            reverse("account-preferences"),
            data={
                "favorite_sodas": ["sprite"],
                "favorite_syrups": ["lime"],
                "favorite_add_ins": ["fresh-mint"],
                "favorite_ice_creams": [],
                "disliked_ingredients": ["coke", "pepsi", "dr-pepper"],
                "dietary_preferences": ["caffeine-free"],
                "sweetness_preference": User.SweetnessPreference.LIGHT,
                "adventurousness_preference": User.AdventurousnessPreference.CLASSIC,
            },
        )

        recommendations = recommend_drinks_for_user(self.user, limit=6)
        self.assertGreater(len(recommendations), 0)

        for row in recommendations:
            menu_item = MENU_ITEMS[row["slug"]]
            base_slug = menu_item["default_soda"]
            base_tags = set(SODA_OPTIONS[base_slug]["tags"])
            self.assertNotIn(
                base_slug,
                {"coke", "pepsi", "dr-pepper"},
                msg=f"{row['slug']} should be de-prioritized by dislike preferences.",
            )
            self.assertNotIn(
                "caffeinated",
                base_tags,
                msg=f"{row['slug']} should honor caffeine-free dietary preference.",
            )

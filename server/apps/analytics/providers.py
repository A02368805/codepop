from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings

from apps.orders.personalization import recommend_drink_menu_scores


@dataclass
class RecommendationProviderResult:
    recommendations: list


class DeterministicRecommendationProvider:
    name = "deterministic"

    def recommend_drinks(self, user, *, limit=4) -> RecommendationProviderResult:
        return RecommendationProviderResult(
            recommendations=recommend_drink_menu_scores(user)[:limit]
        )


class MockExternalRecommendationProvider:
    name = "mock-external"

    def recommend_drinks(self, user, *, limit=4) -> RecommendationProviderResult:
        seeded = recommend_drink_menu_scores(user)[:limit]
        transformed = []
        for row in seeded:
            row_copy = dict(row)
            explanation = row_copy.get("explanation", "")
            row_copy["explanation"] = (
                f"[Mock external provider] {explanation}".strip()
            )
            transformed.append(row_copy)
        return RecommendationProviderResult(recommendations=transformed)


def _provider_name_from_settings() -> str:
    configured = getattr(settings, "AI_RECOMMENDATION_PROVIDER", "deterministic")
    return str(configured or "deterministic").strip().lower()


def get_recommendation_provider():
    provider_name = _provider_name_from_settings()
    if provider_name == MockExternalRecommendationProvider.name:
        return MockExternalRecommendationProvider()
    return DeterministicRecommendationProvider()

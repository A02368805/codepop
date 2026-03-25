from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import time
from urllib import error as url_error
from urllib import request as url_request

from django.conf import settings

from apps.orders.personalization import recommend_drink_menu_scores


logger = logging.getLogger(__name__)


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


class AnthropicRecommendationProvider:
    name = "anthropic"

    def recommend_drinks(self, user, *, limit=4) -> RecommendationProviderResult:
        seeded = recommend_drink_menu_scores(user)[:limit]
        api_key = str(getattr(settings, "ANTHROPIC_API_KEY", "") or "").strip()
        if not api_key or not seeded:
            logger.info(
                "anthropic_provider_skipped",
                extra={
                    "reason": "missing_api_key_or_seeded_rows",
                    "seeded_count": len(seeded),
                },
            )
            return RecommendationProviderResult(recommendations=seeded)

        base_url = str(
            getattr(settings, "ANTHROPIC_API_BASE_URL", "https://api.anthropic.com")
        ).rstrip("/")
        model = str(
            getattr(settings, "ANTHROPIC_MODEL", "claude-3-5-haiku-latest")
        )
        timeout_seconds = float(getattr(settings, "AI_PROVIDER_TIMEOUT_SECONDS", 8))
        max_retries = int(getattr(settings, "AI_PROVIDER_MAX_RETRIES", 2))

        prompt_lines = [
            "Rewrite the explanations for these drink recommendations.",
            "Return JSON only with this shape: {\"recommendations\": [{\"name\": \"...\", \"explanation\": \"...\"}]}",
            "Do not change names. Keep explanations under 120 characters.",
            json.dumps(
                [
                    {"name": row.get("name", ""), "explanation": row.get("explanation", "")}
                    for row in seeded
                ]
            ),
        ]
        body = {
            "model": model,
            "max_tokens": 300,
            "messages": [{"role": "user", "content": "\n".join(prompt_lines)}],
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

                content_blocks = payload.get("content") or []
                text_block = ""
                for block in content_blocks:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text_block = block.get("text", "")
                        break
                if not text_block:
                    raise ValueError("Anthropic response did not contain text content.")

                parsed = json.loads(text_block)
                rewritten = parsed.get("recommendations") or []
                rewritten_by_name = {
                    str(item.get("name", "")): str(item.get("explanation", "")).strip()
                    for item in rewritten
                    if isinstance(item, dict)
                }

                transformed = []
                for row in seeded:
                    row_copy = dict(row)
                    ai_explanation = rewritten_by_name.get(row_copy.get("name", ""), "")
                    if ai_explanation:
                        row_copy["explanation"] = ai_explanation
                    transformed.append(row_copy)
                logger.info(
                    "anthropic_provider_success",
                    extra={
                        "attempt": attempt,
                        "latency_ms": int((time.perf_counter() - started_at) * 1000),
                        "model": model,
                        "result_count": len(transformed),
                    },
                )
                return RecommendationProviderResult(recommendations=transformed)
            except (
                ValueError,
                json.JSONDecodeError,
                TimeoutError,
                url_error.URLError,
                url_error.HTTPError,
            ) as exc:
                logger.warning(
                    "anthropic_provider_attempt_failed",
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

        logger.warning(
            "anthropic_provider_fallback_to_deterministic",
            extra={
                "model": model,
                "seeded_count": len(seeded),
            },
        )
        return RecommendationProviderResult(recommendations=seeded)


def _provider_name_from_settings() -> str:
    configured = getattr(settings, "AI_RECOMMENDATION_PROVIDER", "deterministic")
    return str(configured or "deterministic").strip().lower()


def get_recommendation_provider():
    provider_name = _provider_name_from_settings()
    if provider_name == MockExternalRecommendationProvider.name:
        return MockExternalRecommendationProvider()
    if provider_name == AnthropicRecommendationProvider.name:
        return AnthropicRecommendationProvider()
    return DeterministicRecommendationProvider()

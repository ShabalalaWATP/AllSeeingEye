"""Language/script choices preserve evidence and never invent regional coverage."""

from dataclasses import replace
from typing import get_args

import httpx
import pytest
from httpx import AsyncClient

from ase.adapters.feeds.rss_seeds_regional import REGIONAL_SEEDS
from ase.adapters.research.news import EDITIONS, GoogleNewsResearchProvider
from ase.adapters.research.regional import RegionalFeedResearchProvider
from ase.adapters.translate.language import DEFAULT_LANGUAGES
from ase.api.schemas_profile import ProfileUpdateIn
from ase.api.schemas_reports import ReportCreateIn
from ase.application.reports.prompts import output_guidance
from ase.application.reports.request import ReportRequest
from ase.application.reports.scope import report_scope
from ase.application.reports.templates import TEMPLATES
from ase.domain.languages import LANGUAGES, ReportLanguage, language_capability, matching_text
from ase.domain.research import CollectionStatus
from ase.domain.users import User
from helpers import USER_PASSWORD, bearer, login_token
from research_feed_helpers import CLOCK, QUERY, PublicFeed, item, rss


@pytest.mark.parametrize("code", get_args(ReportLanguage))
def test_report_language_round_trip_and_bounded_prompt(code: str) -> None:
    request = ReportCreateIn.model_validate({"template": "ask", "report_language": code})
    restored = ReportRequest.from_scope("ask", report_scope(request.to_request(), TEMPLATES["ask"]))
    assert restored.report_language == code
    assert ProfileUpdateIn.model_validate({"report_language": code}).report_language == code
    capability = language_capability(code)
    assert capability and capability.report_supported
    guidance = output_guidance(code, "assessment")
    assert "Retain key judgement statements in British English" in guidance
    if code != "en":
        assert capability.label in guidance


def test_catalogue_detector_capabilities_do_not_infer_chinese_script() -> None:
    assert set(get_args(ReportLanguage)) == {
        language.code for language in LANGUAGES if language.report_supported
    }
    assert len(DEFAULT_LANGUAGES) == len(set(DEFAULT_LANGUAGES)) == 24
    assert "fa" in DEFAULT_LANGUAGES and "zh" in DEFAULT_LANGUAGES
    assert "zh-Hans" not in DEFAULT_LANGUAGES and "zh-Hant" not in DEFAULT_LANGUAGES
    for code in ("fa", "ar"):
        capability = language_capability(code)
        assert capability and not capability.pdf_supported
    assert EDITIONS["zh-cn"] == ("zh-CN", "CN", "CN:zh-Hans")
    assert EDITIONS["zh-tw"] == ("zh-TW", "TW", "TW:zh-Hant")


@pytest.mark.parametrize("code", ["fa", "zh", "zh-Hans", "zh-Hant"])
async def test_script_or_language_does_not_invent_a_news_edition(
    monkeypatch: pytest.MonkeyPatch,
    code: str,
) -> None:
    feed = PublicFeed(monkeypatch, httpx.Response(200, text=rss(item())))
    query = replace(QUERY, languages=(code,))
    provider = GoogleNewsResearchProvider(feed.http, CLOCK, code)
    result = await provider.collect(query)
    await feed.http.aclose()
    assert result.attempts[0].status is CollectionStatus.UNSUPPORTED
    assert not feed.requests and not feed.guarded


def test_matching_preserves_zero_width_characters_and_script_distinctions() -> None:
    original = "كی می\u200cرود ي"
    assert matching_text(original, "fa") == "کی می\u200cرود ی"
    assert matching_text(original, "ar") == original
    assert original == "كی می\u200cرود ي"
    assert matching_text("国家", "zh-Hans") != matching_text("國家", "zh-Hant")


async def test_persian_matching_preserves_original_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = "شركت می\u200cرود ايران"
    feed = PublicFeed(monkeypatch, httpx.Response(200, text=rss(item(title=original))))
    seed = next(row for row in REGIONAL_SEEDS if row.spec.id == "hrana_fa")
    result = await RegionalFeedResearchProvider(feed.http, CLOCK, seed).collect(
        replace(QUERY, languages=("fa",), terms=("شرکت", "ایران"))
    )
    await feed.http.aclose()
    assert len(result.items) == 1
    assert result.items[0].title == original
    assert result.items[0].language == "fa"


async def test_profile_catalogue_and_unicode_preferences_round_trip(
    client: AsyncClient,
    user: User,
) -> None:
    assert (await client.get("/api/me/profile/languages")).status_code == 401
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    response = await client.get("/api/me/profile/languages", headers=headers)
    assert response.status_code == 200
    catalogue = {entry["code"]: entry for entry in response.json()["languages"]}
    assert catalogue["fa"]["native_label"] == "فارسی"
    assert catalogue["fa"]["direction"] == "rtl"
    assert catalogue["fa"]["google_news_edition"] is None
    assert catalogue["zh-Hant"]["google_news_edition"] is None
    assert catalogue["zh-TW"]["google_news_edition"]["gl"] == "TW"
    changes = {
        "display_name": "علی می\u200cرود 國家",
        "report_language": "fa",
        "research_languages": ["fa", "zh-Hans", "zh-Hant", "zh", "zh-CN", "zh-TW"],
    }
    saved = await client.patch("/api/me/profile", headers=headers, json=changes)
    assert saved.status_code == 200, saved.text
    loaded = (await client.get("/api/me/profile", headers=headers)).json()
    assert all(loaded[key] == value for key, value in changes.items())

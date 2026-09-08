"""Translation profile selection, untrusted output, usage and app wiring."""

import json
from dataclasses import replace
from uuid import uuid4

import pytest
from httpx import AsyncClient

from ase.adapters.llm.translator import LlmTranslator, parse_translations
from ase.adapters.security.cipher import FernetCipher
from ase.application.ports.translate import TranslatorUnavailable
from ase.application.reports.source_provenance_text import source_provenance_lines
from ase.container import Container
from ase.domain.events import MAX_TITLE
from ase.domain.evidence import EvidenceItem
from ase.domain.llm import LlmProfile, LlmRole
from ase.domain.users import User
from feeds_helpers import make_event
from llm_fixture_helpers import seed_legacy_profile
from report_helpers import PROFILE, ScriptedGateway


async def test_translation_legacy_profile_reaches_store_stream_and_usage(
    container: Container,
    client: AsyncClient,
    admin: User,
) -> None:
    container.llm = gateway = ScriptedGateway('{"translations":["<b>Talks resume</b>"]}')
    queue = container.build_translation_queue()
    event = replace(
        make_event(
            "foreign", title="Les pourparlers reprennent", published_at=container.clock.now()
        ),
        language="fr",
    )
    container.store.upsert([event])
    assert await queue.run_once() == 0  # absence is retried once an admin adds the role
    await seed_legacy_profile(container, {**PROFILE, "roles": ["translation"]})
    stream = container.bus.subscribe()
    assert await queue.run_once() == 1
    message = await anext(aiter(stream))
    assert message.kind == "event.upsert"
    stored = container.store.get(event.id)
    assert stored is not None and stored.title_en == "Talks resume"
    assert stored.title == event.title and stored.content_hash == event.content_hash
    trace = stored.transformations[0]
    assert trace.original_text == event.title and trace.transformed_text == stored.title_en
    assert trace.origin == "machine" and trace.model and trace.profile_id
    assert trace.provider and trace.review_status == "unreviewed"
    evidence = EvidenceItem.from_event(
        "E1", stored, container.clock.now(), source_name="fixture", independence_key="fixture"
    )
    exported = "\n".join(source_provenance_lines(evidence))
    assert f"model: {trace.model}" in exported
    assert f"provider: {trace.provider}" in exported
    assert f"profile: {trace.profile_id}" in exported
    cached_event = replace(event, id="same-title-new-event")
    container.store.upsert([cached_event])
    assert await queue.run_once() == 1
    assert container.store.get(cached_event.id).transformations == stored.transformations
    assert len(gateway.requests) == 1
    assert await queue.run_once() == 0
    request = gateway.requests[0]
    assert request.schema_name == "translation"
    assert request.temperature == 0 and request.max_output_tokens <= PROFILE["max_output_tokens"]
    assert "untrusted" in request.messages[0].content
    async with container.session_factory() as session:
        rows = await container.repositories(session).llm_usage.list_recent(10)
    assert len(rows) == 1
    assert rows[0].purpose == "translation" and rows[0].user_id is None and rows[0].ok
    assert rows[0].prompt_tokens == 50 and rows[0].completion_tokens == 20
    stream.close()


async def test_translation_failures_are_accounted_without_recording_model_content(
    container: Container,
) -> None:
    now = container.clock.now()
    profile = LlmProfile(
        uuid4(),
        "Translator",
        "http://localhost:11434/v1",
        "local",
        container.cipher.encrypt("fixture-secret"),
        "cret",
        frozenset({LlmRole.TRANSLATION}),
        1000,
        0.2,
        True,
        now,
        now,
    )
    async with container.session_factory() as session:
        await container.repositories(session).llm_profiles.add(profile)
        await session.commit()
    container.llm = ScriptedGateway("!fixture-secret", "not json", '{"translations":[""]}')
    queue = container.build_translation_queue()
    for index in range(3):
        container.store.upsert(
            [
                replace(
                    make_event(str(index), published_at=now, title=f"Bonjour {index}"),
                    language="fr",
                )
            ]
        )
        assert await queue.run_once() == 0
    assert queue.calls_this_hour == 3
    async with container.session_factory() as session:
        rows = await container.repositories(session).llm_usage.list_recent(10)
    assert len(rows) == 3 and all(not row.ok for row in rows)
    assert all("fixture-secret" not in (row.error or "") for row in rows)
    assert rows[0].prompt_tokens == 50


async def test_translator_empty_disabled_missing_key_and_unreadable_key(
    container: Container,
) -> None:
    async def no_profile():
        return None

    async def no_usage(usage):
        pytest.fail("Unavailable configuration must not write usage.")

    translator = LlmTranslator(
        no_profile,
        no_usage,
        FernetCipher(None),
        ScriptedGateway(),
        container.clock,
    )
    assert await translator.translate([]) == []
    with pytest.raises(TranslatorUnavailable):
        await translator.translate([("Bonjour", "fr")])
    with pytest.raises(ValueError):
        await translator.translate([("Bonjour", "fr")] * 21)
    with pytest.raises(ValueError):
        await translator.translate([("x" * (MAX_TITLE + 1), "fr")])
    now = container.clock.now()
    profile = LlmProfile(
        uuid4(),
        "Disabled",
        "http://localhost/v1",
        "m",
        "bad-key",
        "",
        frozenset(),
        64,
        0,
        False,
        now,
        now,
    )

    async def lookup():
        return profile

    translator = LlmTranslator(
        lookup,
        no_usage,
        container.cipher,
        ScriptedGateway(),
        container.clock,
    )
    with pytest.raises(TranslatorUnavailable):
        await translator.translate([("Bonjour", "fr")])
    profile.enabled = True
    profile.roles = frozenset({LlmRole.TRANSLATION})
    with pytest.raises(TranslatorUnavailable):
        await translator.translate([("Bonjour", "fr")])


@pytest.mark.parametrize(
    "content",
    [
        "[]",
        "null",
        '{"translations":[]}',
        '{"translations":[1]}',
        '{"translations":["a","b"]}',
        '{"translations":["a"],"extra":true}',
        "x" * (20 * MAX_TITLE * 8 + 1),
    ],
    ids=["array", "null", "missing", "non-string", "extra-item", "extra-field", "oversized"],
)
def test_invalid_translation_response_is_rejected(content: str) -> None:
    with pytest.raises(ValueError):
        parse_translations(content, 1)


def test_translation_titles_are_plain_bounded_text() -> None:
    assert parse_translations('{"translations":["<b> Hello </b>\\u0000 world"]}', 1) == [
        "Hello world"
    ]
    assert len(parse_translations(json.dumps({"translations": ["a" * 1000]}), 1)[0]) == MAX_TITLE

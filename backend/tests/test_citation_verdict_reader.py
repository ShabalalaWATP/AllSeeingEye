"""The evaluation harness loads a real verdict export and reports counts with denominators."""

import json
from datetime import timedelta

import pytest
from evaluations.__main__ import main
from evaluations.citation_verdicts import (
    load_verdict_export,
    read_verdict_files,
    verdict_metrics,
)

from citation_verdict_helpers import MEMBER, make_team, seed_verdict_report, verdict_payload
from helpers import USER_PASSWORD, bearer, create_user, login_token


async def _export(container, client, user, tmp_path):
    second = await create_user(
        container, email="verdict-second@example.com", password=USER_PASSWORD
    )
    team_id = await make_team(container, ((user, MEMBER), (second, MEMBER)))
    _, _, path = await seed_verdict_report(container, user.id, team_id=team_id)
    first = bearer(await login_token(client, user.email, USER_PASSWORD))
    other = bearer(await login_token(client, second.email, USER_PASSWORD))
    for headers, payload in (
        (first, verdict_payload(verdict="cannot_tell")),
        (first, verdict_payload(verdict="supports")),
        (other, verdict_payload(verdict="does_not_support", note=None)),
        (first, verdict_payload(label="E2", verdict="partly_supports")),
        (other, verdict_payload(judgement_id="KJ2", label="E3", verdict="supports")),
    ):
        container.clock.advance(timedelta(seconds=1))
        assert (await client.post(path, headers=headers, json=payload)).status_code == 201
    exported = await client.get(path + "/export", headers=first)
    assert exported.status_code == 200
    target = tmp_path / "verdicts.jsonl"
    target.write_text(exported.text, encoding="utf-8")
    return target


async def test_harness_cli_reads_an_export_with_explicit_denominators(
    container, client, user, tmp_path
):
    export = await _export(container, client, user, tmp_path)
    out = tmp_path / "metrics.json"
    assert main(["verdicts", "--export", str(export), "--out", str(out)]) == 0
    metrics = json.loads(out.read_text(encoding="utf-8"))
    assert "human opinions" in metrics["attribution"].lower()
    assert "accuracy" not in {key.lower() for key in metrics}
    assert (metrics["verdicts_read"], metrics["superseded_verdicts"]) == (5, 1)
    assert (metrics["current_verdicts"], metrics["citations_with_verdicts"]) == (4, 3)
    assert metrics["by_verdict"]["supports"] == {"count": 2, "denominator": 4, "rate": 0.5}
    assert metrics["by_verdict"]["cannot_tell"]["count"] == 0
    assert metrics["by_relation"]["contradicting"]["supports"] == {
        "count": 0,
        "denominator": 0,
        "rate": None,
    }
    assert metrics["citations_with_reviewer_disagreement"] == {
        "count": 1,
        "denominator": 1,
        "rate": 1.0,
    }
    assert metrics["citations_with_a_does_not_support_verdict"]["denominator"] == 3
    # The same export twice is merged by verdict id rather than double counted.
    assert len(read_verdict_files([export, export])) == 5
    with pytest.raises(SystemExit):
        main(["verdicts", "--export", str(export), "--out", str(out)])


async def test_reader_rejects_altered_bindings_and_other_datasets(
    container, client, user, tmp_path
):
    export = await _export(container, client, user, tmp_path)
    lines = export.read_text(encoding="utf-8").splitlines()
    header, row = json.loads(lines[0]), json.loads(lines[1])

    def rejected(records):
        with pytest.raises(ValueError):
            load_verdict_export([json.dumps(record) for record in records])

    rejected([header, {**row, "judgement_statement": "A different claim."}])
    rejected([header, *[json.loads(line) for line in lines[1:]][:-1]])
    rejected([{**header, "dataset": "evaluation-review"}, row])
    rejected([header, {**row, "report_version_id": header["report_id"]}])
    rejected([header, {**row, "verdict": "true"}])
    if row["excerpt"] is not None:
        rejected([header, {**row, "excerpt": {**row["excerpt"], "text": "altered"}}])
    rejected([row])
    rejected([])
    changed = tmp_path / "changed.jsonl"
    altered = {**row, "note": "Changed note."}
    altered_lines = [lines[0], json.dumps(altered), *lines[2:]]
    changed.write_text("\n".join(altered_lines), encoding="utf-8")
    with pytest.raises(ValueError):
        read_verdict_files([export, changed])
    assert verdict_metrics([], files=0)["by_verdict"]["supports"]["rate"] is None

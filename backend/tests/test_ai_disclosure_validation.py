"""Malformed disclosure input is rejected before starting the isolated browser."""

from unittest.mock import Mock

import pytest

from ase.adapters.reports import chromium_pdf_child


@pytest.mark.parametrize(
    "payload",
    [
        None,
        "bad-json",
        '"bad"',
        "{}",
        '{"model": "x", "provider": "made-up"}',
        '{"model": "x", "provider": "bedrock", "extra": true}',
        " " * 16_385,
    ],
)
def test_child_rejects_missing_invalid_or_oversized_disclosure(tmp_path, monkeypatch, payload):
    monkeypatch.chdir(tmp_path)
    if payload is not None:
        (tmp_path / "disclosure.json").write_text(payload)
    launch = Mock(side_effect=AssertionError("Browser must not start"))
    monkeypatch.setattr(chromium_pdf_child.subprocess, "run", launch)
    assert chromium_pdf_child.main() == 1
    launch.assert_not_called()

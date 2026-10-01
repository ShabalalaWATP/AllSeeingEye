"""Typed board subjects carry a version only for report versions."""

from __future__ import annotations

from uuid import uuid4

import pytest

from ase.domain.team_board import BoardSubject, BoardSubjectKind, BoardSubjectView


def test_report_versions_need_a_positive_version_and_other_kinds_refuse_one() -> None:
    subject_id = uuid4()
    assert BoardSubject(BoardSubjectKind.REPORT_VERSION, subject_id, 3).version == 3
    assert BoardSubject(BoardSubjectKind.SAVED_AREA, subject_id).version is None
    assert BoardSubject(BoardSubjectKind.DRAWING_COLLECTION, subject_id).version is None
    for kind, version in (
        (BoardSubjectKind.REPORT_VERSION, None),
        (BoardSubjectKind.REPORT_VERSION, 0),
        (BoardSubjectKind.SAVED_AREA, 1),
        (BoardSubjectKind.DRAWING_COLLECTION, 2),
    ):
        with pytest.raises(ValueError):
            BoardSubject(kind, subject_id, version)


def test_an_unavailable_view_never_carries_a_title() -> None:
    subject = BoardSubject(BoardSubjectKind.SAVED_AREA, uuid4())
    assert BoardSubjectView(subject, "Northern approaches").available
    hidden = BoardSubjectView.unavailable(subject)
    assert not hidden.available and hidden.title is None

"""Large sensor batches never enter quadratic narrative headline clustering."""

from unittest.mock import Mock

from ase.adapters.feeds.firms import SPEC
from ase.application.feeds.grading import profiles_from_specs
from ase.domain import grading
from ase.domain.events import Credibility
from feeds_helpers import make_event


def test_five_thousand_sensor_labels_stay_individual_and_do_not_corroborate_news(monkeypatch):
    sensors = [
        make_event(str(index), source_id=SPEC.id, title="NOAA-20 VIIRS thermal detection")
        for index in range(5_000)
    ]
    report = make_event("report", source_id="news", title="NOAA-20 VIIRS thermal detection")
    original = grading.build_stories
    cluster = Mock(wraps=original)
    monkeypatch.setattr(grading, "build_stories", cluster)
    result = grading.grade_events([*sensors, report], profiles_from_specs([SPEC]))
    cluster.assert_called_once_with([report])
    assert len(result) == 5_001
    assert len({item.story_id for item in result}) == 5_001
    assert all(item.credibility is Credibility.PROBABLY_TRUE for item in result[1:])
    assert result[0].credibility is Credibility.CANNOT_BE_JUDGED
    assert "5000 other" not in result[0].rationale
    assert all("related topic" not in item.rationale for item in result)

"""Missing or unsupported linked geometry stops a job before external background work."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from ase.application.reports.job_preparation import ReportJobBuilder
from ase.application.reports.request import ReportRequest
from ase.application.reports.templates import template_for
from ase.domain.collection import CollectionPlan, Pir
from ase.domain.errors import InvalidRequest
from test_exact_reusable_areas import triangle
from test_warning import NOW


@pytest.mark.parametrize("missing", [True, False])
async def test_area_guard_precedes_background_and_job_creation(missing):
    aois = Mock()
    aois.get = AsyncMock(
        return_value=None if missing else SimpleNamespace(research_area=triangle())
    )
    provider = AsyncMock(return_value="background")
    builder = ReportJobBuilder(Mock(), Mock(), aois, {"ask": provider})
    # A valid question keeps this regression focused on the geometry admission,
    # which must still happen before the external background provider is called.
    plan = CollectionPlan(
        uuid4(),
        "plan",
        "",
        uuid4(),
        (),
        (Pir("P1", "What changed?"),),
        True,
        uuid4(),
        NOW,
        NOW,
    )
    with pytest.raises(InvalidRequest, match="unavailable" if missing else "cannot honour"):
        await builder.build(
            Mock(),
            template_for("ask"),
            ReportRequest(template_id="ask", question="What changed?"),
            Mock(),
            NOW,
            plan=plan,
        )
    provider.assert_not_awaited()

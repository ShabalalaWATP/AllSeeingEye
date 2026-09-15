from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from ase.adapters.persistence import (
    models,  # noqa: F401
    teams,  # noqa: F401
)
from ase.adapters.persistence.base import Base
from ase.adapters.persistence.subscription_comparisons import (
    SqlSubscriptionComparisonRepository,
)
from ase.adapters.persistence.subscription_edition_models import SubscriptionEditionRow
from ase.domain.errors import Conflict
from ase.domain.research_changes import (
    ChangeClassification,
    ComparisonReason,
    ComparisonState,
)
from ase.domain.subscription_comparisons import EditionComparison

NOW = datetime(2026, 9, 14, 12, tzinfo=UTC)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_append_once_comparison_roundtrip_rejects_rewrite(tmp_path) -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'comparison.db'}")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    edition_id, previous_id, current_id = uuid4(), uuid4(), uuid4()
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with factory() as session:
        session.add(
            SubscriptionEditionRow(
                id=edition_id,
                subscription_id=uuid4(),
                trigger="scheduled",
                due_at_utc=NOW,
                request_uuid=None,
                frozen_revision=1,
                requested_start=NOW - timedelta(days=1),
                requested_end=NOW,
                effective_intervals=[],
                gaps=[],
                compatibility_fingerprint="a" * 64,
                baseline_version_id=previous_id,
                workflow="completed",
                report_quality="ready",
                coverage="complete_for_plan",
                created_at=NOW,
                updated_at=NOW,
                revision=2,
                job_id=None,
                report_id=uuid4(),
                version_id=current_id,
                safe_reason=None,
                covered_by_edition_id=None,
                accepted_as_baseline=False,
            )
        )
        await session.flush()
        comparison = EditionComparison(
            edition_id,
            previous_id,
            current_id,
            ChangeClassification(
                ComparisonState.NO_NEW_RELEVANT_EVIDENCE,
                (ComparisonReason.ADEQUATE_COVERAGE_NO_NEW_EVIDENCE,),
            ),
            NOW,
        )
        repository = SqlSubscriptionComparisonRepository(session)
        assert await repository.add(comparison) == comparison
        assert await repository.add(comparison) == comparison
        assert await repository.list_for([edition_id]) == {edition_id: comparison}
        with pytest.raises(Conflict, match="different immutable"):
            await repository.add(
                EditionComparison(
                    edition_id,
                    previous_id,
                    current_id,
                    ChangeClassification(ComparisonState.ASSESSMENT_CHANGED, ()),
                    NOW,
                )
            )
    await engine.dispose()

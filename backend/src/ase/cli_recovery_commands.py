"""Lightweight command declarations keep migration startup independent of application wiring."""

from pathlib import Path
from typing import Annotated
from uuid import UUID

import typer

app = typer.Typer(help="Protected manual recovery records; never starts services.")
JournalPath = Annotated[Path, typer.Option(help="Absolute protected journal path outside backups")]
KeyPath = Annotated[Path, typer.Option(help="Absolute independent recovery key path")]
Operator = Annotated[UUID, typer.Option(help="Operator UUID attributed by trusted-host access")]


@app.command("journal")
def journal(
    action: Annotated[str, typer.Argument(help="initialise, inspect or resolve")],
    journal: JournalPath,
    key: KeyPath,
    event: Annotated[UUID | None, typer.Option()] = None,
    operator: Annotated[UUID | None, typer.Option()] = None,
    outcome: Annotated[str | None, typer.Option(help="applied or not_applied")] = None,
    evidence: Annotated[
        str | None, typer.Option(help="SHA-256 of protected investigation evidence")
    ] = None,
    head: Annotated[str | None, typer.Option(help="Current inspection head_sha256")] = None,
) -> None:
    """Create new history explicitly, inspect records, or attest an investigated intent."""
    from ase.cli_recovery import journal_action, output  # noqa: PLC0415

    output(lambda: journal_action(action, journal, key, event, operator, outcome, evidence, head))


@app.command("restriction")
def restriction(
    journal: JournalPath,
    key: KeyPath,
    operator: Operator,
    owner: Annotated[UUID, typer.Option()],
    restriction: Annotated[
        str, typer.Option(help="deactivate, objection or a named channel opt-out")
    ],
    target: Annotated[
        UUID | None, typer.Option(help="Required for subscription_opt_out only")
    ] = None,
    purpose: Annotated[str, typer.Option()] = "rights_request",
    days: Annotated[int, typer.Option(help="Next review in 1 to 90 days")] = 90,
) -> None:
    """Record a restrictive instruction; this does not change the account or delivery."""
    from ase.cli_recovery import output, record_restriction  # noqa: PLC0415

    output(
        lambda: record_restriction(
            journal,
            key,
            operator,
            owner,
            restriction,
            target,
            purpose,
            days,
        )
    )


@app.command("copy-review")
def copy_review(
    journal: JournalPath,
    key: KeyPath,
    operator: Operator,
    reference: Annotated[
        UUID, typer.Option(help="Opaque ID of a separate protected copy inventory")
    ],
    category: Annotated[
        str, typer.Option(help="scheduled, manual, offsite, release, mailbox, export, snapshot")
    ],
    purpose: Annotated[str, typer.Option()] = "quarterly",
    days: Annotated[int, typer.Option(help="Next review in 1 to 90 days")] = 90,
    max_age_days: Annotated[
        int | None, typer.Option(help="Actually selected maximum age, if any")
    ] = None,
    keep_count: Annotated[
        int | None, typer.Option(help="Actually selected retained count, if any")
    ] = None,
    hold: Annotated[
        bool, typer.Option(help="Explicit preservation hold; review date is not expiry")
    ] = False,
) -> None:
    """Record a selected policy and due date; never delete or certify external copies."""
    from ase.cli_recovery import output, record_copy_review  # noqa: PLC0415

    output(
        lambda: record_copy_review(
            journal,
            key,
            operator,
            reference,
            category,
            purpose,
            days,
            max_age_days,
            keep_count,
            hold,
        )
    )

"""Reviewed private graph ownership and its disposable projections.

These explicit relationships also cover logical links without database foreign
keys. A new table is never added to a removal merely because it has a foreign key.
"""

from uuid import UUID

from ase.adapters.persistence.base import Base
from ase.adapters.persistence.private_removal_graph import RemovalGraph
from ase.adapters.persistence.private_removal_selection import RemovalInventory
from ase.domain.private_removal import RemovalRequest, RemovalScope


def _private(inventory: RemovalInventory, name: str, owner: UUID, column: str) -> None:
    table = Base.metadata.tables[name]
    predicate = table.c[column] == owner
    if "team_id" in table.c:
        predicate &= table.c.team_id.is_(None)
    inventory.add(name, predicate)


def graph_inventory(graph: RemovalGraph, request: RemovalRequest) -> RemovalInventory:
    inventory = RemovalInventory()
    for name, key, ids in (
        ("reports", "id", graph.report_ids),
        ("schedules", "id", graph.schedule_ids),
        ("report_jobs", "id", graph.job_ids),
        ("research_brief_revisions", "brief_id", graph.brief_ids),
    ):
        inventory.add(name, Base.metadata.tables[name].c[key].in_(ids))
    # Report children. Source-report team-copy provenance is intentionally independent.
    for name in (
        "report_versions",
        "report_embeddings",
        "report_team_copies",
        "original_assets",
        "claims",
        "identity_decisions",
        "relationship_reviews",
        "map_views",
        "citation_verdicts",
        "research_library",
        "research_library_tags",
        "source_review_snapshots",
        "report_ledger_heads",
        "annotation_monitors",
    ):
        inventory.child(name, "report_id", "reports")
    for child, column, parent in (
        ("claim_revisions", "claim_id", "claims"),
        ("identity_decision_revisions", "decision_id", "identity_decisions"),
        ("relationship_review_revisions", "relationship_id", "relationship_reviews"),
        ("map_view_revisions", "view_id", "map_views"),
        ("report_ledger_entries", "ledger_id", "report_ledger_heads"),
        ("forecast_review_reminders", "ledger_id", "report_ledger_heads"),
        ("original_passage_assets", "report_version_id", "report_versions"),
        ("original_passage_assets", "job_id", "report_jobs"),
        ("report_job_monthly_usage", "job_id", "report_jobs"),
    ):
        inventory.child(child, column, parent)
    for name in (
        "subscription_revisions",
        "subscription_editions",
        "subscription_lineages",
        "selected_index_records",
        "selected_index_cursors",
        "selected_index_losses",
        "subscription_notification_preferences",
    ):
        inventory.child(name, "subscription_id", "schedules")
    for name in (
        "subscription_delivery_outbox",
        "subscription_edition_attempts",
        "subscription_edition_comparisons",
    ):
        inventory.child(name, "edition_id", "subscription_editions")
    if request.scope is RemovalScope.ACCOUNT:
        account_inventory(inventory, request.owner_id)
    # Own alerts may contain frozen private inputs independently of their report.
    for column, parent in (
        ("report_id", "reports"),
        ("report_job_id", "report_jobs"),
        ("schedule_id", "schedules"),
        ("annotation_monitor_id", "annotation_monitors"),
    ):
        inventory.child("alerts", column, parent)
    for name in (
        "annotation_monitor_watches",
        "annotation_revision_outbox",
        "annotation_monitor_transitions",
    ):
        inventory.child(name, "monitor_id", "annotation_monitors")
    inventory.child("alert_notification_outbox", "alert_id", "alerts")
    inventory.child("web_push_outbox", "alert_id", "alerts")
    return inventory


def account_inventory(inventory: RemovalInventory, owner: UUID) -> None:
    # Keep accounting, shared content, audit, invitations and attribution references.
    for name in (
        "password_tokens",
        "refresh_tokens",
        "refresh_family_activity",
        "admin_totp",
        "email_mfa",
        "mfa_challenges",
        "mfa_recovery_codes",
        "private_feed_tokens",
        "notification_preferences",
        "notification_digest_preferences",
        "subscription_notification_preferences",
        "web_push_devices",
        "research_library",
        "research_library_tags",
        "research_tiers",
    ):
        _private(inventory, name, owner, "user_id")
    for name, column in (
        ("assistant_conversations", "owner_id"),
        ("aois", "created_by"),
        ("collection_plans", "created_by"),
        ("indicators", "created_by"),
        ("alerts", "created_by"),
        ("annotation_monitors", "created_by"),
        ("map_workspace_documents", "created_by"),
        ("source_review_heads", "owner_id"),
        ("alert_webhook_destinations", "created_by"),
    ):
        _private(inventory, name, owner, column)
    inventory.child("web_push_outbox", "device_id", "web_push_devices")
    inventory.child("source_review_revisions", "head_key", "source_review_heads", "key")
    inventory.child("alert_notification_routes", "indicator_id", "indicators")
    inventory.child("warning_consumption", "indicator_id", "indicators")
    # Additional personal tables are registered with the application's repositories.
    for name in (
        "personal_profiles",
        "directory_profiles",
        "directory_avatars",
        "bell_preferences",
        "bell_rule_mutes",
        "team_board_read_cursors",
    ):
        _private(inventory, name, owner, "user_id")
    # These are the recipient's private state, although linked to shared teams.
    for name, column in (
        ("team_board_read_cursors", "user_id"),
        ("team_board_mentions", "recipient_id"),
    ):
        inventory.add(name, Base.metadata.tables[name].c[column] == owner)
    _private(inventory, "llm_connection_bindings", owner, "user_id")
    memberships = Base.metadata.tables["team_memberships"]
    inventory.add("team_memberships", memberships.c.user_id == owner)

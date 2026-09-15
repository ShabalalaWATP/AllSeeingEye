"""Add administrator controlled AI allowance policies, overrides, a ledger and totals."""

import sqlalchemy as sa
from alembic import op

revision = "0045"
down_revision = "0044"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_usage_policies",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("scope", sa.String(12), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=True),
        sa.Column("period", sa.String(8), nullable=False),
        sa.Column("request_limit", sa.Integer(), nullable=True),
        sa.Column("token_limit", sa.Integer(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("scope IN ('global','system','user','team')", name="ck_ai_policy_scope"),
        sa.CheckConstraint("period IN ('day','week','month')", name="ck_ai_policy_period"),
        sa.CheckConstraint(
            "request_limit IS NULL OR request_limit >= 0", name="ck_ai_policy_requests"
        ),
        sa.CheckConstraint("token_limit IS NULL OR token_limit >= 0", name="ck_ai_policy_tokens"),
        sa.CheckConstraint(
            "(scope IN ('global','system') AND target_id IS NULL) OR "
            "(scope IN ('user','team') AND target_id IS NOT NULL)",
            name="ck_ai_policy_target",
        ),
    )
    op.create_index("ix_ai_usage_policies_scope", "ai_usage_policies", ["scope"])
    op.create_index("ix_ai_usage_policies_target_id", "ai_usage_policies", ["target_id"])

    op.create_table(
        "ai_usage_counters",
        sa.Column(
            "policy_id",
            sa.Uuid(),
            sa.ForeignKey("ai_usage_policies.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("period_start", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_requests", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reserved_requests", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("used_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reserved_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.CheckConstraint("used_requests >= 0", name="ck_ai_counter_used_requests"),
        sa.CheckConstraint("reserved_requests >= 0", name="ck_ai_counter_reserved_requests"),
        sa.CheckConstraint("used_tokens >= 0", name="ck_ai_counter_used_tokens"),
        sa.CheckConstraint("reserved_tokens >= 0", name="ck_ai_counter_reserved_tokens"),
    )

    op.create_table(
        "ai_usage_reservations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("call_id", sa.Uuid(), nullable=False),
        sa.Column(
            "policy_id",
            sa.Uuid(),
            sa.ForeignKey("ai_usage_policies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("team_id", sa.Uuid(), nullable=True),
        sa.Column("system", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("profile_id", sa.Uuid(), sa.ForeignKey("llm_profiles.id"), nullable=True),
        sa.Column("model", sa.String(2048), nullable=False),
        sa.Column("purpose", sa.String(64), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reserved_tokens", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("actual_tokens", sa.Integer(), nullable=True),
        sa.Column("ok", sa.Boolean(), nullable=True),
        sa.Column("error", sa.String(120), nullable=True),
        sa.CheckConstraint(
            "status IN ('reserved','settled','released','unknown')",
            name="ck_ai_reservation_status",
        ),
        sa.CheckConstraint("reserved_tokens >= 1", name="ck_ai_reservation_tokens"),
        sa.CheckConstraint(
            "actual_tokens IS NULL OR actual_tokens >= 0", name="ck_ai_actual_tokens"
        ),
        sa.CheckConstraint(
            "(system = true AND user_id IS NULL AND team_id IS NULL) OR "
            "(system = false AND user_id IS NOT NULL)",
            name="ck_ai_reservation_attribution",
        ),
    )
    for column in ("call_id", "policy_id", "user_id", "team_id", "created_at"):
        op.create_index(f"ix_ai_usage_reservations_{column}", "ai_usage_reservations", [column])
    op.create_index(
        "ix_ai_usage_reservations_status_created",
        "ai_usage_reservations",
        ["status", "created_at"],
    )
    _create_overrides_and_totals()


def _create_overrides_and_totals() -> None:
    states = "('inherit','limit','unlimited','blocked')"
    op.create_table(
        "ai_usage_policy_overrides",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "policy_id",
            sa.Uuid(),
            sa.ForeignKey("ai_usage_policies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("request_state", sa.String(12), nullable=False),
        sa.Column("request_limit", sa.Integer(), nullable=True),
        sa.Column("token_state", sa.String(12), nullable=False),
        sa.Column("token_limit", sa.Integer(), nullable=True),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(f"request_state IN {states}", name="ck_ai_override_request_state"),
        sa.CheckConstraint(f"token_state IN {states}", name="ck_ai_override_token_state"),
        sa.CheckConstraint(
            "(request_state = 'limit' AND request_limit IS NOT NULL AND request_limit >= 0) OR "
            "(request_state <> 'limit' AND request_limit IS NULL)",
            name="ck_ai_override_request_limit",
        ),
        sa.CheckConstraint(
            "(token_state = 'limit' AND token_limit IS NOT NULL AND token_limit >= 0) OR "
            "(token_state <> 'limit' AND token_limit IS NULL)",
            name="ck_ai_override_token_limit",
        ),
        sa.CheckConstraint("expires_at > effective_from", name="ck_ai_override_window"),
    )
    op.create_index(
        "ix_ai_usage_overrides_policy_window",
        "ai_usage_policy_overrides",
        ["policy_id", "expires_at"],
    )
    op.create_table(
        "ai_usage_totals",
        sa.Column("period_start", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("team_key", sa.Uuid(), primary_key=True),
        sa.Column("user_key", sa.Uuid(), primary_key=True),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_requests", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("used_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unknown_requests", sa.Integer(), nullable=False, server_default="0"),
        sa.CheckConstraint("used_requests >= 0", name="ck_ai_total_used_requests"),
        sa.CheckConstraint("used_tokens >= 0", name="ck_ai_total_used_tokens"),
        sa.CheckConstraint("unknown_requests >= 0", name="ck_ai_total_unknown_requests"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    for name in (
        "ai_usage_totals",
        "ai_usage_policy_overrides",
        "ai_usage_reservations",
        "ai_usage_counters",
        "ai_usage_policies",
    ):
        if bind.scalar(sa.select(sa.func.count()).select_from(sa.table(name))):
            raise RuntimeError("Refusing downgrade: AI usage records remain.")
    op.drop_table("ai_usage_totals")
    op.drop_index("ix_ai_usage_overrides_policy_window", table_name="ai_usage_policy_overrides")
    op.drop_table("ai_usage_policy_overrides")
    op.drop_index("ix_ai_usage_reservations_status_created", table_name="ai_usage_reservations")
    for column in ("call_id", "policy_id", "user_id", "team_id", "created_at"):
        op.drop_index(f"ix_ai_usage_reservations_{column}", table_name="ai_usage_reservations")
    op.drop_table("ai_usage_reservations")
    op.drop_table("ai_usage_counters")
    op.drop_index("ix_ai_usage_policies_target_id", table_name="ai_usage_policies")
    op.drop_index("ix_ai_usage_policies_scope", table_name="ai_usage_policies")
    op.drop_table("ai_usage_policies")

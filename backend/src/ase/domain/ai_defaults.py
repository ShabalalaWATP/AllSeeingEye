"""The secure starting set of AI allowance policies.

Fresh and previously unconfigured installations receive the site and system policies
through migration 0061. Administrators can edit them and can apply the per-account
policy to active accounts from the allowance workspace.

The numbers below were chosen against five measured days on the operator's own install:
about 969,000 tokens and 912 provider calls, dominated by report generation, of which
roughly 99,000 tokens were unattended background work (conflict screening and feed
translation).  That is about 194,000 tokens a day in total and about 20,000 a day of
background work.  The site-wide daily figure of 300,000 is therefore roughly 1.5 times
the measured average, not a large margin: an administrator who wants real slack should
raise it before adopting the set.
"""

from __future__ import annotations

from dataclasses import dataclass

from ase.domain.ai_usage import AiAllowancePeriod, AiPolicyScope

# Site-wide daily token ceiling covering every account and every purpose.
DEFAULT_SITE_DAILY_TOKENS = 300_000
# Thirty days of the daily figure, so a quiet week cannot be spent in one evening.
DEFAULT_SITE_MONTHLY_TOKENS = 9_000_000
# Unattended background work: feed translation, conflict screening and digests.
DEFAULT_SYSTEM_DAILY_TOKENS = 100_000
# One account cannot exceed the whole site's day. Applied to each active account.
DEFAULT_PERSON_DAILY_TOKENS = 300_000


@dataclass(frozen=True, slots=True)
class AiDefaultPolicy:
    """One suggested policy. ``per_active_user`` fans out to every active account."""

    scope: AiPolicyScope
    period: AiAllowancePeriod
    token_limit: int
    reason: str
    per_active_user: bool = False


DEFAULT_POLICY_SET: tuple[AiDefaultPolicy, ...] = (
    AiDefaultPolicy(
        AiPolicyScope.GLOBAL,
        AiAllowancePeriod.DAY,
        DEFAULT_SITE_DAILY_TOKENS,
        "A daily ceiling for the whole site, so one bad day cannot run away.",
    ),
    AiDefaultPolicy(
        AiPolicyScope.GLOBAL,
        AiAllowancePeriod.MONTH,
        DEFAULT_SITE_MONTHLY_TOKENS,
        "A monthly ceiling of thirty daily budgets, so the bill stays predictable.",
    ),
    AiDefaultPolicy(
        AiPolicyScope.SYSTEM,
        AiAllowancePeriod.DAY,
        DEFAULT_SYSTEM_DAILY_TOKENS,
        "A separate daily budget for unattended background work.",
    ),
    AiDefaultPolicy(
        AiPolicyScope.USER,
        AiAllowancePeriod.DAY,
        DEFAULT_PERSON_DAILY_TOKENS,
        "A daily ceiling for each active account, so one person cannot spend the site.",
        per_active_user=True,
    ),
)

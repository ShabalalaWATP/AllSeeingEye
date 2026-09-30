import { describe, expect, it } from 'vitest';

import type { LlmConnection, LlmProfile } from '@/lib/api/llm';
import { aiPolicy, aiPreview, aiSummary, aiTotals } from '@/test/fixtures.aiUsage';
import { adminUser, llmProfiles, plainUser, source, sourceHealth } from '@/test/fixtures';

import {
  compactNumber,
  describeAction,
  summariseConnections,
  summariseSources,
  summariseTeams,
  summariseUsage,
  summariseUsers,
} from './overviewSummaries';

const [draft] = llmProfiles as [LlmProfile];
const bound: LlmProfile = {
  ...draft,
  id: '99999999-9999-4999-8999-999999999999',
  is_bound: true,
  is_tested: true,
  tested_revision: 1,
};
function binding(overrides: Partial<LlmConnection>): LlmConnection {
  return {
    team_id: null,
    user_id: null,
    profile_id: bound.id,
    profile_revision: 1,
    tested_config_hash: 'hash',
    activated_at: '2026-09-01T00:00:00Z',
    activated_by: adminUser.id,
    revision: 1,
    ...overrides,
  };
}

describe('overview summaries', () => {
  it('counts active accounts, administrators and dormant accounts', () => {
    expect(
      summariseUsers([
        adminUser,
        { ...adminUser, id: 'a2', is_active: false },
        plainUser,
        { ...plainUser, id: 'u2', last_login_at: '2026-09-01T00:00:00Z' },
      ]),
    ).toEqual({ total: 4, active: 3, inactive: 1, admins: 1, neverSignedIn: 1 });
  });

  it('separates active and archived teams', () => {
    const team = {
      id: 't',
      name: 'Desk',
      is_active: true,
      created_by: adminUser.id,
      created_at: '',
      updated_at: '',
      description: null,
    };
    expect(summariseTeams([team, { ...team, id: 't2', is_active: false }])).toEqual({
      total: 2,
      active: 1,
      archived: 1,
    });
  });

  it('groups source health and orders the attention list', () => {
    const minor = source({
      id: 'minor',
      health: sourceHealth({ status: 'degraded', consecutive_failures: 1 }),
    });
    const major = source({
      id: 'major',
      health: sourceHealth({ status: 'degraded', consecutive_failures: 7 }),
    });
    const blocked = source({
      id: 'blocked',
      environment_disabled: true,
      health: sourceHealth({ status: 'disabled' }),
    });
    const off = source({ id: 'off', enabled: false, health: sourceHealth({ status: 'idle' }) });
    const waiting = source({ id: 'waiting', health: sourceHealth({ status: 'idle' }) });
    const summary = summariseSources([source(), minor, major, blocked, off, waiting]);
    expect(summary).toMatchObject({
      total: 6,
      healthy: 1,
      failing: 2,
      idle: 1,
      switchedOff: 1,
      blockedByOperator: 1,
    });
    expect(summary.attention.map((item) => item.id)).toEqual(['major', 'minor', 'blocked']);
  });

  it('counts upstream refusals separately from failing feeds', () => {
    const refused = source({
      id: 'refused',
      health: sourceHealth({
        status: 'degraded',
        consecutive_failures: 0,
        blocked_reason: 'The publisher refuses automated clients.',
      }),
    });
    const failing = source({
      id: 'failing',
      health: sourceHealth({ status: 'degraded', consecutive_failures: 3 }),
    });
    const summary = summariseSources([refused, failing]);
    expect(summary).toMatchObject({ failing: 1, blockedUpstream: 1 });
    expect(summary.attention.map((item) => item.id)).toEqual(['failing', 'refused']);
  });

  it('separates on-demand capabilities from scheduled health and uses disjoint counts', () => {
    const items = [
      source(),
      source({ id: 'research', test_available: false, health: sourceHealth({ status: 'idle' }) }),
      source({ id: 'research-stale-health', test_available: false }),
      source({ id: 'off-healthy', enabled: false }),
      source({
        id: 'off-failing',
        enabled: false,
        health: sourceHealth({ status: 'degraded', consecutive_failures: 3 }),
      }),
      source({
        id: 'breaker',
        enabled: true,
        health: sourceHealth({ status: 'disabled', consecutive_failures: 8 }),
      }),
      source({
        id: 'environment',
        environment_disabled: true,
        enabled: false,
        health: sourceHealth({ status: 'degraded', blocked_reason: 'Upstream refusal.' }),
      }),
      source({ id: 'first-poll', health: sourceHealth({ status: 'idle' }) }),
    ];
    const summary = summariseSources(items);
    expect(summary).toMatchObject({
      total: 8,
      scheduled: 6,
      onDemand: 2,
      healthy: 1,
      failing: 1,
      idle: 1,
      switchedOff: 2,
      blockedByOperator: 1,
      blockedUpstream: 0,
    });
    expect(summary.attention.map((item) => item.id)).toEqual(['breaker', 'environment']);
    expect(
      summary.healthy +
        summary.failing +
        summary.idle +
        summary.switchedOff +
        summary.blockedByOperator +
        summary.blockedUpstream,
    ).toBe(summary.scheduled);
  });

  it('describes the global connection, overrides and drafts', () => {
    const status = summariseConnections({ items: [bound, draft], encryption_available: true }, [
      binding({}),
      binding({ team_id: '22222222-2222-4222-8222-222222222222' }),
      binding({ user_id: plainUser.id }),
    ]);
    expect(status).toEqual({
      encryption: true,
      global: { name: draft.name, model: draft.model, tested: true },
      legacy: 0,
      teamOverrides: 1,
      personalOverrides: 1,
      drafts: 1,
      untestedDrafts: 1,
    });
  });

  it('reports legacy role selection and missing global profiles', () => {
    const legacy = summariseConnections({ items: [draft], encryption_available: false }, []);
    expect(legacy).toMatchObject({ global: null, legacy: 1, encryption: false });
    const orphan = summariseConnections({ items: [], encryption_available: true }, [binding({})]);
    expect(orphan).toMatchObject({ global: null, legacy: 0 });
    const stale = summariseConnections(
      { items: [{ ...bound, revision: 2 }], encryption_available: true },
      [binding({})],
    );
    expect(stale.global?.tested).toBe(false);
  });

  it('picks site-wide and system allowances from a system preview', () => {
    const site = aiSummary({ policy: aiPolicy({ scope: 'global' }) });
    const system = aiSummary({ policy: aiPolicy({ id: 'x', scope: 'system' }) });
    expect(
      summariseUsage(
        aiPreview({
          items: [system, site],
          observed: aiTotals({ used_requests: 4, used_tokens: 900 }),
          unknown_calls: 2,
        }),
      ),
    ).toEqual({
      site,
      system,
      systemRequests: 4,
      systemTokens: 900,
      unknownCalls: 2,
      periodEnd: '2026-10-01T00:00:00Z',
    });
    expect(summariseUsage(aiPreview()).site).toBeNull();
  });

  it('formats action names and compact numbers for reading', () => {
    expect(describeAction('account_request_approved')).toBe('Account request approved');
    expect(describeAction('llm.connection_applied')).toBe('LLM connection applied');
    expect(describeAction('AI_usage')).toBe('AI usage');
    expect(describeAction('___')).toBe('___');
    expect(compactNumber(612_400)).toBe('612.4K');
  });
});

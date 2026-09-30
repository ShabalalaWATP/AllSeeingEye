import { describe, expect, it } from 'vitest';

import { aiPolicy, teamId } from '@/test/fixtures.aiUsage';
import { adminUser } from '@/test/fixtures';
import { team } from '@/test/fixtures.teams';

import { describeOverrideLimit, parseLimit, policyLabel } from './aiUsagePresentation';

const knownTeam = { ...team, id: teamId, name: 'Northern desk' };
const missingId = '99999999-9999-4999-8999-999999999999';

describe('parseLimit', () => {
  it('treats blank as unlimited and accepts whole non-negative numbers', () => {
    expect(parseLimit('   ')).toBeNull();
    expect(parseLimit('0')).toBe(0);
    expect(parseLimit(' 25 ')).toBe(25);
  });

  it('rejects fractions, negatives, text and unsafe integers', () => {
    for (const value of ['1.5', '-1', 'ten', '9007199254740993']) {
      expect(parseLimit(value)).toBeNaN();
    }
  });
});

describe('policyLabel', () => {
  it('names untargeted scopes', () => {
    expect(policyLabel(aiPolicy({ scope: 'global' }), [], [])).toBe('Everyone');
    expect(policyLabel(aiPolicy({ scope: 'system' }), [], [])).toBe('System work');
    expect(policyLabel(aiPolicy({ scope: 'user', target_id: null }), [], [])).toBe('user');
  });

  it('names known and unknown user targets', () => {
    const known = aiPolicy({ scope: 'user', target_id: adminUser.id });
    expect(policyLabel(known, [adminUser], [])).toBe(
      `User · ${adminUser.display_name} (${adminUser.email})`,
    );
    const unknown = aiPolicy({ scope: 'user', target_id: missingId });
    expect(policyLabel(unknown, [adminUser], [])).toBe(`User · ${missingId}`);
  });

  it('names known and unknown team targets', () => {
    const known = aiPolicy({ scope: 'team', target_id: teamId });
    expect(policyLabel(known, [], [knownTeam])).toBe('Team · Northern desk');
    const unknown = aiPolicy({ scope: 'team', target_id: missingId });
    expect(policyLabel(unknown, [], [knownTeam])).toBe(`Team · ${missingId}`);
  });
});

describe('describeOverrideLimit', () => {
  it('distinguishes a zero limit, a numeric limit and a missing value', () => {
    expect(describeOverrideLimit('limit', 0)).toBe('Blocked (0)');
    expect(describeOverrideLimit('limit', 40)).toBe('40');
    expect(describeOverrideLimit('limit', null)).toBe('0');
  });

  it('labels the named states and falls back to the raw state', () => {
    expect(describeOverrideLimit('inherit', null)).toBe('Keep policy limit');
    expect(describeOverrideLimit('unlimited', null)).toBe('Unlimited');
    expect(describeOverrideLimit('blocked', null)).toBe('Blocked');
    expect(describeOverrideLimit('paused' as never, null)).toBe('paused');
  });
});

import { describe, expect, it } from 'vitest';

import type { LlmConnection, LlmProfile } from '@/lib/api/llm';
import { adminUser, llmProfiles } from '@/test/fixtures';

import { setupChecklist, type SetupState } from './setupChecklist';

const [draft] = llmProfiles as [LlmProfile];
const tested: LlmProfile = { ...draft, is_tested: true, tested_revision: 1, is_bound: true };
const globalBinding: LlmConnection = {
  team_id: null,
  user_id: null,
  profile_id: tested.id,
  profile_revision: 1,
  tested_config_hash: 'hash',
  activated_at: '2026-09-01T00:00:00Z',
  activated_by: adminUser.id,
  revision: 1,
};

function state(overrides: Partial<SetupState> = {}): SetupState {
  return {
    profiles: { items: [], encryption_available: true },
    connections: [],
    emailRelay: false,
    osMaps: false,
    feedsContact: false,
    ...overrides,
  };
}

const doneById = (value: SetupState) =>
  Object.fromEntries(setupChecklist(value).steps.map((step) => [step.id, step.done]));

describe('setup checklist', () => {
  it('starts with every essential AI step outstanding on a fresh installation', () => {
    const result = setupChecklist(state());
    expect(result.essentialDone).toBe(false);
    expect(result.allDone).toBe(false);
    expect(result.remainingOptional).toBe(3);
    expect(result.steps.filter((step) => step.essential).map((step) => step.to)).toEqual([
      '/admin/llm',
      '/admin/llm',
      '/admin/llm',
    ]);
    expect(doneById(state())).toMatchObject({ connect: false, test: false, assign: false });
  });

  it('ignores embedding-only models and untested or changed drafts', () => {
    const embeddings: LlmProfile = { ...tested, id: 'embed', roles: ['embeddings'] };
    expect(
      doneById(state({ profiles: { items: [embeddings], encryption_available: true } })),
    ).toMatchObject({ connect: false, test: false });
    expect(
      doneById(state({ profiles: { items: [draft], encryption_available: true } })),
    ).toMatchObject({ connect: true, test: false, assign: false });
    const edited: LlmProfile = { ...tested, revision: 2 };
    expect(
      doneById(
        state({
          profiles: { items: [edited], encryption_available: true },
          connections: [globalBinding],
        }),
      ),
    ).toMatchObject({ connect: true, test: false, assign: false });
  });

  it('needs a tested app-default assignment, not only a team override', () => {
    const profiles = { items: [tested], encryption_available: true };
    expect(doneById(state({ profiles }))).toMatchObject({ test: true, assign: false });
    const teamOnly = { ...globalBinding, team_id: 'team-a' };
    expect(doneById(state({ profiles, connections: [teamOnly] }))).toMatchObject({
      assign: false,
    });
    const result = setupChecklist(state({ profiles, connections: [globalBinding] }));
    expect(result.essentialDone).toBe(true);
    expect(result.allDone).toBe(false);
  });

  it('counts unknown optional checks as outstanding and finishes when all are done', () => {
    const essentials = {
      profiles: { items: [tested], encryption_available: true },
      connections: [globalBinding],
    };
    const unknown = setupChecklist(
      state({ ...essentials, emailRelay: null, osMaps: true, feedsContact: true }),
    );
    expect(unknown.remainingOptional).toBe(1);
    expect(unknown.steps.find((step) => step.id === 'email')).toMatchObject({
      done: null,
      setting: 'ASE_SMTP_HOST and ASE_SMTP_FROM_EMAIL',
    });
    const all = setupChecklist(
      state({ ...essentials, emailRelay: true, osMaps: true, feedsContact: true }),
    );
    expect(all).toMatchObject({ essentialDone: true, allDone: true, remainingOptional: 0 });
  });
});

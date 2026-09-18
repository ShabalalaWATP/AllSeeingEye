import { http, HttpResponse } from 'msw';

import type { LlmConnection, LlmProfile, LlmProfileInput } from '@/lib/api/llm';
import { adminUser, llmProfiles } from '@/test/fixtures';
import { team } from '@/test/fixtures.teams';
import { server } from '@/test/server';

export { team };
export const proof = 'a'.repeat(64);
function requiredProfile(value: LlmProfile | undefined): LlmProfile {
  if (value === undefined) throw new Error('Missing test profile');
  return value;
}
export function draft(overrides: Partial<LlmProfile> = {}): LlmProfile {
  return {
    ...requiredProfile(llmProfiles[0]),
    name: 'OpenAI Luna',
    base_url: 'https://api.openai.com/v1',
    model: 'gpt-5.6-luna',
    enabled: false,
    roles: ['direction', 'assessment', 'devil', 'translation'],
    reasoning_effort: 'max',
    max_output_tokens: 16000,
    ...overrides,
  };
}
export function binding(profile: LlmProfile, teamId: string | null = null): LlmConnection {
  return {
    team_id: teamId,
    profile_id: profile.id,
    profile_revision: profile.revision,
    tested_config_hash: proof,
    activated_at: '2026-09-06T12:00:00Z',
    activated_by: adminUser.id,
    revision: 1,
  };
}

/** Mutable synthetic API, including saved revisions and their test proof. No external calls. */
export function installConnections(initial = [draft()], initialBindings: LlmConnection[] = []) {
  const state = {
    profiles: initial,
    bindings: initialBindings,
    tests: 0,
    models: 0,
    saves: [] as LlmProfileInput[],
  };
  server.use(
    http.post('/api/admin/llm/models/discover', () => {
      state.models += 1;
      return HttpResponse.json({ models: ['gpt-5.6-luna', 'manual-alternative'] });
    }),
    http.get('/api/teams', () => HttpResponse.json({ items: [team] })),
    http.get('/api/admin/llm/profiles', () =>
      HttpResponse.json({ items: state.profiles, encryption_available: true }),
    ),
    http.get('/api/admin/llm/connections', () => HttpResponse.json({ items: state.bindings })),
    http.post('/api/admin/llm/profiles', async ({ request }) => {
      const body = (await request.json()) as LlmProfileInput;
      state.saves.push(body);
      const saved = draft({
        ...body,
        id: '77777777-7777-4777-8777-777777777777',
        roles: body.roles ?? [],
        api_key_hint: 'test',
      });
      state.profiles.push(saved);
      return HttpResponse.json(saved, { status: 201 });
    }),
    http.put('/api/admin/llm/profiles/:id', async ({ request, params }) => {
      const body = (await request.json()) as LlmProfileInput;
      state.saves.push(body);
      const current = requiredProfile(state.profiles.find((profile) => profile.id === params.id));
      const saved = {
        ...current,
        ...body,
        roles: body.roles ?? [],
        revision: current.revision + 1,
        is_tested: false,
        tested_revision: null,
        tested_config_hash: null,
        tested_at: null,
      };
      state.profiles = state.profiles.map((profile) => (profile.id === saved.id ? saved : profile));
      return HttpResponse.json(saved);
    }),
    http.post('/api/admin/llm/profiles/:id/test', ({ params }) => {
      state.tests++;
      const current = requiredProfile(state.profiles.find((profile) => profile.id === params.id));
      Object.assign(current, {
        is_tested: true,
        tested_revision: current.revision,
        tested_config_hash: proof,
        tested_at: '2026-09-06T12:00:00Z',
      });
      return HttpResponse.json({
        ok: true,
        latency_ms: 812.4,
        model: current.model,
        error: null,
        revision: current.revision,
        tested_config_hash: proof,
        tested_at: current.tested_at,
      });
    }),
    http.delete('/api/admin/llm/profiles/:id', ({ params }) => {
      state.profiles = state.profiles.filter((profile) => profile.id !== params.id);
      return new HttpResponse(null, { status: 204 });
    }),
  );
  return state;
}

import { http, HttpResponse } from 'msw';
import type { AiPolicy } from '@/lib/api/aiUsage';
import type { ModelWorkspaceInput } from '@/lib/api/modelWorkspace';
import { server } from '@/test/server';
import { binding, draft, installConnections, proof } from './llmTestFixtures';
import { allowancePresetLimits } from './modelAllowancePresets';

export const luna = draft({
  name: 'Luna',
  is_bound: true,
  is_tested: true,
  tested_revision: 1,
  tested_config_hash: proof,
});
export const sol = draft({
  id: '88888888-8888-4888-8888-888888888888',
  name: 'Sol',
  model: 'gpt-5.6-sol',
  is_tested: true,
  tested_revision: 1,
  tested_config_hash: proof,
});

export function installModelWorkspace(profiles = [luna, sol], bindings = [binding(luna)]) {
  const state = installConnections(profiles, bindings);
  const workspace = { state, policies: [] as AiPolicy[], writes: [] as ModelWorkspaceInput[] };
  server.use(
    http.get('/api/admin/ai-usage/policies', () => HttpResponse.json(workspace.policies)),
    http.put('/api/admin/llm/workspace', async ({ request }) => {
      const body = (await request.json()) as ModelWorkspaceInput;
      workspace.writes.push(body);
      for (const change of body.changes) {
        const teamId = change.scope === 'team' ? (change.target_id ?? null) : null;
        const userId = change.scope === 'user' ? (change.target_id ?? null) : null;
        if (change.model) {
          state.bindings = state.bindings.filter(
            (item) => item.team_id !== teamId || (item.user_id ?? null) !== userId,
          );
          const profile = state.profiles.find((item) => item.id === change.model?.profile_id);
          if (profile)
            state.bindings.push({
              ...binding(profile, teamId),
              user_id: userId,
              revision: workspace.writes.length + 1,
            });
        }
        if (change.allowance) {
          workspace.policies = workspace.policies.filter(
            (item) => item.scope !== change.scope || item.target_id !== change.target_id,
          );
          if (change.allowance.preset !== 'inherit')
            workspace.policies.push({
              id: '99999999-9999-4999-8999-999999999999',
              scope: change.scope,
              target_id: change.target_id ?? null,
              period: 'day',
              enabled: true,
              revision: workspace.writes.length,
              created_at: '2026-09-17T12:00:00Z',
              updated_at: '2026-09-17T12:00:00Z',
              ...allowancePresetLimits(change.allowance.preset),
            });
        }
      }
      return HttpResponse.json({ connections: state.bindings, policies: workspace.policies });
    }),
  );
  return workspace;
}

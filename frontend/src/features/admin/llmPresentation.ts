import type { LlmProfile, LlmRole } from '@/lib/api/llm';

export const OPENAI_BASE_URL = 'https://api.openai.com/v1';
export const LUNA_MODEL = 'gpt-5.6-luna';
export const LUNA_MAX_OUTPUT_TOKENS = 32_000;
export const TEXT_ROLES: LlmRole[] = ['direction', 'assessment', 'devil', 'translation'];
export const ROLE_LABELS: Record<LlmRole, string> = {
  direction: 'Research planning',
  assessment: 'Report writing',
  devil: 'Evidence review',
  translation: 'Translation',
  embeddings: 'Report search',
};

/** Mirrors legacy first-enabled-per-role selection in the server's profile order. */
export function legacyConnections(profiles: readonly LlmProfile[]) {
  const selected = new Map<string, { profile: LlmProfile; roles: LlmRole[] }>();
  for (const role of TEXT_ROLES) {
    const profile = profiles.find((item) => item.enabled && item.roles.includes(role));
    if (profile === undefined) continue;
    const existing = selected.get(profile.id);
    if (existing) existing.roles.push(role);
    else selected.set(profile.id, { profile, roles: [role] });
  }
  return [...selected.values()];
}

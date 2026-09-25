import { fetchCapabilities } from '@/lib/api/capabilities';

import { useScopedResource } from './useScopedResource';

/**
 * Whether this installation can run AI research for the signed-in account: `true`, `false`,
 * or `null` while unknown (loading, failed or an older server). Only `false` should prompt
 * a notice; an unknown answer never blocks a form, and submission still reports failures.
 */
export function useAiResearchReady(): boolean | null {
  const { data } = useScopedResource(fetchCapabilities);
  return data?.ai_research ?? null;
}

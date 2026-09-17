import { fetchLlmProfiles, fetchLlmConnections } from '@/lib/api/llm';
import { listTeams } from '@/lib/api/teams';
import { listUsers } from '@/lib/api/admin';
import { listAiPolicies } from '@/lib/api/aiUsage';
/** Admin user listing is complete, not a paginated first page. */
export async function loadConnections() {
  const [profiles, connections, teams, users, policies] = await Promise.all([
    fetchLlmProfiles(),
    fetchLlmConnections(),
    listTeams(),
    listUsers(),
    listAiPolicies(),
  ]);
  return { profiles, connections, teams, users, policies };
}

import { fetchLlmProfiles, fetchLlmConnections } from '@/lib/api/llm';
import { listTeams } from '@/lib/api/teams';
import { listUsers } from '@/lib/api/admin';
/** Admin user listing is complete, not a paginated first page. */
export async function loadConnections() {
  const [profiles, connections, teams, users] = await Promise.all([
    fetchLlmProfiles(),
    fetchLlmConnections(),
    listTeams(),
    listUsers(),
  ]);
  return { profiles, connections, teams, users };
}

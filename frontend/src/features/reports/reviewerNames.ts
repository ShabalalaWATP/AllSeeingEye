import type { TeamDetail } from '@/lib/api/teams';

/**
 * A reviewer's display name from rosters the reader can already see. The server returns
 * only the reviewer's account id, so an unknown id is described rather than guessed.
 */
export function reviewerName(
  reviewerId: string,
  actorId: string | null | undefined,
  teams: readonly TeamDetail[],
): string {
  if (actorId && reviewerId === actorId) return 'You';
  for (const detail of teams) {
    const member = detail.members.find((entry) => entry.user_id === reviewerId);
    if (member) return member.display_name;
  }
  return 'Another reviewer (not in your current team rosters)';
}

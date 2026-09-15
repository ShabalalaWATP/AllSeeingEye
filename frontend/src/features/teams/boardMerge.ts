import type { TeamBoardPost } from '@/lib/api/teamBoard';

export function newestPost(posts: readonly TeamBoardPost[]): TeamBoardPost | undefined {
  return posts.reduce<TeamBoardPost | undefined>(
    (latest, post) => (latest === undefined || post.created_at > latest.created_at ? post : latest),
    undefined,
  );
}

/** Append an older page, letting the fresher copy of any duplicate win. */
export function appendPage(
  current: readonly TeamBoardPost[],
  incoming: readonly TeamBoardPost[],
): TeamBoardPost[] {
  const known = new Set(incoming.map((post) => post.id));
  return [...current.filter((post) => !known.has(post.id)), ...incoming];
}

/**
 * Merge a refreshed first page without dropping older pages the user has loaded.
 * The first page keeps server order at the top; posts it no longer contains stay
 * below in their existing order. A newer local revision is never replaced by an
 * older response.
 */
export function mergeFirstPage(
  current: readonly TeamBoardPost[],
  incoming: readonly TeamBoardPost[],
): TeamBoardPost[] {
  const existing = new Map(current.map((post) => [post.id, post]));
  const top = incoming.map((post) => {
    const known = existing.get(post.id);
    return known !== undefined && known.revision >= post.revision ? known : post;
  });
  const fresh = new Set(incoming.map((post) => post.id));
  return [...top, ...current.filter((post) => !fresh.has(post.id))];
}

/** Count posts in a refreshed page that were not already on screen. */
export function countNewPosts(
  current: readonly TeamBoardPost[],
  incoming: readonly TeamBoardPost[],
): number {
  const known = new Set(current.map((post) => post.id));
  return incoming.filter((post) => !known.has(post.id)).length;
}

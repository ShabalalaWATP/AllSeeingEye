/**
 * Whose work a list shows. Every role starts with "mine": their personal records and the
 * records of teams they currently belong to. Only administrators may widen a list to "all",
 * and only by an explicit, visible choice kept in the address. The server applies the same
 * scope before limits and counts; this module only chooses what to ask for and how to label it.
 */
export type OwnershipScope = 'mine' | 'all';

export const OWNERSHIP_PARAM = 'scope';

/** Anything but an administrator's explicit `scope=all` is "mine". */
export function parseOwnershipScope(value: string | null, isAdmin: boolean): OwnershipScope {
  return isAdmin && value === 'all' ? 'all' : 'mine';
}

/** A record's owner: a team workspace, or a personal owner the server named. */
export interface OwnedRecord {
  team_id: string | null;
  ownerId: string | null;
  ownerName?: string | null | undefined;
}

/**
 * "Personal" only for the viewer's own records, so another person's record is never
 * mistaken for the viewer's. Team records keep their workspace label.
 */
export function ownerLabel(
  record: OwnedRecord,
  teamLabel: (teamId: string) => string,
  viewerId: string | undefined,
): string {
  if (record.team_id) return teamLabel(record.team_id);
  if (record.ownerId !== null && record.ownerId === viewerId) return 'Personal';
  return `Personal: ${record.ownerName ?? 'another user'}`;
}

/** Whether acting on this record changes another person's personal work. */
export function belongsToSomeoneElse(record: OwnedRecord, viewerId: string | undefined): boolean {
  return !record.team_id && record.ownerId !== viewerId;
}

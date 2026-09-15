import type { User } from '@/lib/api/schemas';
import type { TeamDetail, TeamMember } from '@/lib/api/teams';

/**
 * Team membership is the source of truth for team authority. The account role
 * remains useful for site-wide administration, but a user's membership in a
 * team decides what they can do inside that team.
 */
export interface TeamCapabilities {
  isAdmin: boolean;
  isMember: boolean;
  isManager: boolean;
  teamIsActive: boolean;
  canCreateTeam: boolean;
  canManageMembers: boolean;
  canManageTeam: boolean;
  canLeave: boolean;
}

export function teamCapabilities(user: User, detail: TeamDetail | null): TeamCapabilities {
  const isAdmin = user.role === 'admin';
  const membership = detail?.members.find((member) => member.user_id === user.id);
  const isMember = membership?.is_active === true;
  const isManager = membership?.is_active === true && membership.role === 'manager';
  const activeTeam = detail?.team.is_active === true;

  return {
    isAdmin,
    isMember,
    isManager,
    teamIsActive: activeTeam,
    // Team creation is available to every authenticated account. The API also
    // creates the caller's first manager membership atomically.
    canCreateTeam: user.is_active,
    canManageMembers: activeTeam && (isAdmin || isManager),
    // Administrators retain the recovery controls for archived teams. Team
    // managers can edit only while the team is active.
    canManageTeam: isAdmin || (activeTeam && isManager),
    // A manager cannot leave a team if that would remove its last manager. The
    // server enforces the invariant; this flag only controls the affordance.
    // Administrators ask another administrator to remove their membership.
    canLeave: activeTeam && isMember && !isAdmin,
  };
}

/** A removed membership or hidden team reads as 403 or 404: stop showing and refreshing it. */
export function isTeamAccessLoss(status: number): boolean {
  return status === 403 || status === 404;
}

export interface MemberCapabilities {
  canChangeRole: boolean;
  canRemove: boolean;
}

/** Derive row actions without duplicating account and membership rules in JSX. */
export function memberCapabilities(
  actor: User,
  member: TeamMember,
  team: Pick<TeamDetail['team'], 'is_active'>,
  canManageMembers: boolean,
): MemberCapabilities {
  if (!team.is_active || !actor.is_active || member.user_id === actor.id) {
    return { canChangeRole: false, canRemove: false };
  }

  const admin = actor.role === 'admin';
  const manager = canManageMembers && !admin;

  // Administrators may administer any non-self account. Team managers can
  // administer ordinary user accounts while administrator accounts stay
  // protected from team-level changes.
  const canChangeRole = admin || (manager && member.account_role === 'user');
  const canRemove = admin || (manager && member.account_role === 'user');
  return { canChangeRole, canRemove };
}

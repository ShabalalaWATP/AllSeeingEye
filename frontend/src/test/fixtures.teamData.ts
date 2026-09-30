import type { User } from '@/lib/api/schemas';
import type { Team, TeamDetail, TeamMember } from '@/lib/api/teams';

import { adminUser, plainUser } from './fixtures';

export const manager: User = {
  ...plainUser,
  id: '33333333-3333-4333-8333-333333333333',
  role: 'manager',
  email: 'manager@example.com',
  display_name: 'Mina Manager',
};
export const team: Team = {
  id: '44444444-4444-4444-8444-444444444444',
  name: 'Northern desk',
  is_active: true,
  created_by: adminUser.id,
  created_at: '2026-09-06T10:00:00Z',
  updated_at: '2026-09-06T10:00:00Z',
  description: null,
};
function member(user: User, role: TeamMember['role']): TeamMember {
  return {
    user_id: user.id,
    display_name: user.display_name,
    username: user.id === manager.id ? 'mina_manager' : null,
    account_role: user.role,
    is_active: user.is_active,
    role,
    joined_at: team.created_at,
  };
}
export const roster: TeamDetail = {
  team,
  members: [member(manager, 'manager'), member(plainUser, 'member')],
};

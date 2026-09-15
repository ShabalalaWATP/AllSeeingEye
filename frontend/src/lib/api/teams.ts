/** Team contracts come from OpenAPI; responses are validated before rendering. */
import { z } from 'zod';

import { apiCall, apiSend } from './client';
import type { components } from './types.gen';

export type Team = components['schemas']['TeamOut'];
export type TeamDetail = components['schemas']['TeamDetailOut'];
export type TeamMember = components['schemas']['MemberOut'];
export type MemberInput = components['schemas']['MemberIn'];
export type TeamUpdate = components['schemas']['TeamUpdateIn'];

const teamSchema = z.object({
  id: z.uuid(),
  name: z.string(),
  is_active: z.boolean(),
  created_by: z.uuid(),
  created_at: z.string(),
  updated_at: z.string(),
  // Older deployments may omit the optional description while migrations are
  // being rolled out. Normalise that response to the contract's null value.
  description: z.string().nullable().default(null),
}) satisfies z.ZodType<Team>;

const teamsSchema = z.object({ items: z.array(teamSchema) }) satisfies z.ZodType<
  components['schemas']['TeamsOut']
>;
const detailSchema = z.object({
  team: teamSchema,
  members: z.array(
    z.object({
      user_id: z.uuid(),
      email: z.string(),
      display_name: z.string(),
      account_role: z.enum(['user', 'manager', 'admin']),
      is_active: z.boolean(),
      role: z.enum(['member', 'manager']),
      joined_at: z.string(),
    }),
  ),
}) satisfies z.ZodType<TeamDetail>;
const membershipSchema = z.object({
  team_id: z.uuid(),
  user_id: z.uuid(),
  role: z.enum(['member', 'manager']),
  joined_at: z.string(),
}) satisfies z.ZodType<components['schemas']['MembershipOut']>;

export async function listTeams(): Promise<Team[]> {
  return (await apiCall('/api/teams', { schema: teamsSchema })).items;
}
export function getTeam(id: string): Promise<TeamDetail> {
  return apiCall(`/api/teams/${encodeURIComponent(id)}`, { schema: detailSchema });
}
export function createTeam(name: string, description?: string): Promise<Team> {
  const body: components['schemas']['TeamIn'] = description ? { name, description } : { name };
  return apiCall('/api/teams', { method: 'POST', body, schema: teamSchema });
}
export function updateTeam(id: string, body: TeamUpdate): Promise<Team> {
  return apiCall(`/api/teams/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    body,
    schema: teamSchema,
  });
}
export function setMember(id: string, body: MemberInput) {
  return apiCall(`/api/teams/${encodeURIComponent(id)}/members`, {
    method: 'PUT',
    body,
    schema: membershipSchema,
  });
}
export function removeMember(id: string, userId: string): Promise<void> {
  return apiSend(`/api/teams/${encodeURIComponent(id)}/members/${encodeURIComponent(userId)}`, {
    method: 'DELETE',
  });
}

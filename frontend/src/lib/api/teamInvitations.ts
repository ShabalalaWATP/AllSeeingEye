/** Team invitations; all responses are validated before entering the UI. */
import { z } from 'zod';

import { apiCall, apiSend } from './client';

const invitationSchema = z.object({
  id: z.uuid(),
  team_id: z.uuid(),
  recipient_id: z.uuid(),
  inviter_id: z.uuid(),
  role: z.enum(['member', 'manager']),
  note: z.string().nullable(),
  status: z.enum(['pending', 'accepted', 'declined', 'withdrawn', 'expired']),
  created_at: z.string(),
  expires_at: z.string(),
  responded_at: z.string().nullable(),
  revision: z.number().int().positive(),
  team_name: z.string().nullable(),
  inviter_display_name: z.string().nullable(),
  recipient_display_name: z.string().nullable(),
  recipient_username: z.string().nullable(),
});

const pageSchema = z.object({
  items: z.array(invitationSchema),
  total: z.number().int().nonnegative(),
  offset: z.number().int().nonnegative(),
  limit: z.number().int().positive(),
  next_offset: z.number().int().nonnegative().nullable(),
});

export type TeamInvitation = z.infer<typeof invitationSchema>;

export function listTeamInvitations(teamId: string): Promise<z.infer<typeof pageSchema>> {
  return apiCall(`/api/teams/${encodeURIComponent(teamId)}/invitations`, {
    schema: pageSchema,
  });
}

export function listMyTeamInvitations(): Promise<z.infer<typeof pageSchema>> {
  return apiCall('/api/me/team-invitations', { schema: pageSchema });
}

export function sendTeamInvitation(
  teamId: string,
  recipientId: string,
  note?: string,
): Promise<TeamInvitation> {
  const body = note?.trim()
    ? { recipient_id: recipientId, note: note.trim() }
    : { recipient_id: recipientId };
  return apiCall(`/api/teams/${encodeURIComponent(teamId)}/invitations`, {
    method: 'POST',
    body,
    schema: invitationSchema,
  });
}

export function withdrawTeamInvitation(
  teamId: string,
  invitationId: string,
  expectedRevision: number,
): Promise<void> {
  return apiSend(
    `/api/teams/${encodeURIComponent(teamId)}/invitations/${encodeURIComponent(invitationId)}?expected_revision=${expectedRevision}`,
    { method: 'DELETE' },
  );
}

function respondToInvitation(
  action: 'accept' | 'decline',
  invitationId: string,
  expectedRevision: number,
): Promise<TeamInvitation> {
  return apiCall(`/api/me/team-invitations/${encodeURIComponent(invitationId)}/${action}`, {
    method: 'POST',
    body: { expected_revision: expectedRevision },
    schema: invitationSchema,
  });
}

export function acceptTeamInvitation(
  invitationId: string,
  expectedRevision: number,
): Promise<TeamInvitation> {
  return respondToInvitation('accept', invitationId, expectedRevision);
}

export function declineTeamInvitation(
  invitationId: string,
  expectedRevision: number,
): Promise<TeamInvitation> {
  return respondToInvitation('decline', invitationId, expectedRevision);
}

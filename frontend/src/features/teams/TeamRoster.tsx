import { useState } from 'react';

import { Button } from '@/components/ui/Button';
import { Table, Td, Th } from '@/components/ui/Table';
import type { User } from '@/lib/api/schemas';
import type { TeamMember } from '@/lib/api/teams';

import { memberCapabilities } from './teamCapabilities';
import { useCompactRoster } from './useCompactRoster';

export function ConfirmAction({
  label,
  question,
  busy,
  onConfirm,
}: {
  label: string;
  question: string;
  busy: boolean;
  onConfirm: () => void;
}) {
  const [confirming, setConfirming] = useState(false);
  if (!confirming)
    return (
      <Button
        variant="danger"
        className="min-h-11"
        disabled={busy}
        onClick={() => {
          setConfirming(true);
        }}
      >
        {label}
      </Button>
    );
  return (
    <div className="flex flex-wrap items-center gap-2" role="group" aria-label={question}>
      <p className="w-full text-sm">{question}</p>
      <Button variant="danger" className="min-h-11" busy={busy} onClick={onConfirm}>
        Confirm {label.toLowerCase()}
      </Button>
      <Button
        variant="ghost"
        className="min-h-11"
        disabled={busy}
        onClick={() => {
          setConfirming(false);
        }}
      >
        Cancel
      </Button>
    </div>
  );
}

interface TeamRosterProps {
  members: TeamMember[];
  actor: User;
  team: { is_active: boolean };
  canManage: boolean;
  busy: boolean;
  onRemove: (member: TeamMember) => void;
  onRole: (member: TeamMember, role: 'member' | 'manager') => void;
}

function MemberActions({
  member,
  actor,
  team,
  canManage,
  busy,
  onRemove,
  onRole,
}: Omit<TeamRosterProps, 'members' | 'admin'> & { member: TeamMember }) {
  const permissions = memberCapabilities(actor, member, team, canManage);
  const isSelf = member.user_id === actor.id;
  return (
    <div className="flex flex-wrap gap-2">
      {permissions.canChangeRole && member.is_active ? (
        <Button
          variant="secondary"
          className="min-h-11"
          disabled={busy}
          onClick={() => onRole(member, member.role === 'manager' ? 'member' : 'manager')}
        >
          {member.role === 'manager' ? 'Set as member' : 'Make manager'}
        </Button>
      ) : null}
      {permissions.canRemove ? (
        <ConfirmAction
          label="Remove member"
          question={`Remove ${member.display_name} from this team?`}
          busy={busy}
          onConfirm={() => onRemove(member)}
        />
      ) : null}
      {isSelf ? <span className="self-center text-xs text-muted">You</span> : null}
      {!isSelf &&
      !permissions.canChangeRole &&
      !permissions.canRemove &&
      member.account_role !== 'user' ? (
        <span className="self-center text-xs text-muted">Administrator protected</span>
      ) : null}
    </div>
  );
}

export function TeamRoster({
  members,
  actor,
  team,
  canManage,
  busy,
  onRemove,
  onRole,
}: TeamRosterProps) {
  const compact = useCompactRoster();
  if (!members.length) return <p className="py-5 text-sm text-muted">No members in this team.</p>;
  if (compact)
    return (
      <ul aria-label="Team members" className="divide-y divide-line border-y border-line">
        {members.map((member) => (
          <li key={member.user_id} className="flex min-w-0 flex-col gap-3 py-4">
            <div>
              <p className="break-words font-medium">{member.display_name}</p>
              {member.username ? (
                <p className="mt-1 break-all text-sm text-muted">@{member.username}</p>
              ) : null}
            </div>
            <dl className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <dt className="text-xs text-muted">Account</dt>
                <dd className="mt-1 capitalize">
                  {member.account_role}
                  {!member.is_active ? <span className="ml-2 text-muted">Inactive</span> : null}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-muted">Team role</dt>
                <dd className="mt-1 capitalize">{member.role}</dd>
              </div>
            </dl>
            {canManage ? (
              <MemberActions
                member={member}
                actor={actor}
                team={team}
                canManage={canManage}
                busy={busy}
                onRemove={onRemove}
                onRole={onRole}
              />
            ) : null}
          </li>
        ))}
      </ul>
    );
  return (
    <Table caption="Team members">
      <thead>
        <tr>
          <Th>Member</Th>
          <Th>Account</Th>
          <Th>Team role</Th>
          {canManage ? <Th>Actions</Th> : null}
        </tr>
      </thead>
      <tbody>
        {members.map((member) => (
          <tr key={member.user_id}>
            <Td>
              <span className="font-medium">{member.display_name}</span>
              {member.username ? (
                <span className="block break-all text-xs text-muted">@{member.username}</span>
              ) : null}
            </Td>
            <Td>
              <span className="capitalize">{member.account_role}</span>
              {!member.is_active ? <span className="block text-muted">Inactive</span> : null}
            </Td>
            <Td>
              <span className="capitalize">{member.role}</span>
            </Td>
            {canManage ? (
              <Td>
                <MemberActions
                  member={member}
                  actor={actor}
                  team={team}
                  canManage={canManage}
                  busy={busy}
                  onRemove={onRemove}
                  onRole={onRole}
                />
              </Td>
            ) : null}
          </tr>
        ))}
      </tbody>
    </Table>
  );
}

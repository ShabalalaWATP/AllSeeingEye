import { useState } from 'react';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SelectField } from '@/components/ui/Field';
import { listUsers } from '@/lib/api/admin';
import { describeError } from '@/lib/api/errors';
import type { TeamDetail, TeamUpdate } from '@/lib/api/teams';

import { useTeamsResource } from './useTeams';

interface ReactivationProps {
  actorId: string;
  busy: boolean;
  onReactivate: (body: TeamUpdate) => void;
}

/** Administrator recovery keeps manager appointment and reactivation in one request. */
export function TeamReactivation({ detail, ...props }: ReactivationProps & { detail: TeamDetail }) {
  if (!detail.members.some((member) => member.role === 'manager' && member.is_active))
    return <ManagerRecovery {...props} />;
  return (
    <Button
      variant="secondary"
      busy={props.busy}
      onClick={() => props.onReactivate({ is_active: true })}
    >
      Reactivate team
    </Button>
  );
}

function ManagerRecovery({ actorId, busy, onReactivate }: ReactivationProps) {
  const accounts = useTeamsResource(listUsers);
  const [selected, setSelected] = useState('');
  const candidates = accounts.data?.filter((user) => user.is_active && user.id !== actorId) ?? [];
  const manager = candidates.find((user) => user.id === selected);
  if (accounts.loading) return <LoadingNote label="Loading eligible Managers" />;
  if (accounts.error)
    return (
      <Alert tone="error">
        {describeError(accounts.error)}{' '}
        <Button variant="ghost" onClick={() => void accounts.reload()}>
          Retry accounts
        </Button>
      </Alert>
    );
  return (
    <form
      aria-label="Reactivate team with a Manager"
      className="flex flex-col items-start gap-3"
      onSubmit={(event) => {
        event.preventDefault();
        if (!busy && manager)
          onReactivate({ is_active: true, reactivation_manager_id: manager.id });
      }}
    >
      <p className="text-sm text-muted">
        This team has no active Manager. Choose an active account to manage it on reactivation.
      </p>
      {candidates.length === 0 ? (
        <p className="text-sm text-muted">
          Activate another account in Users, then refresh the roster to try again.
        </p>
      ) : (
        <SelectField
          label="Manager on reactivation"
          hint="The selected account will join this team as a Manager if it is not already a member."
          required
          disabled={busy}
          value={manager?.id ?? ''}
          onChange={(event) => setSelected(event.target.value)}
          options={[
            { value: '', label: 'Choose an active account' },
            ...candidates.map((user) => ({
              value: user.id,
              label: `${user.display_name} (${user.email})`,
            })),
          ]}
        />
      )}
      <Button type="submit" variant="secondary" busy={busy} disabled={!manager}>
        Reactivate team
      </Button>
    </form>
  );
}

import { PersonCell } from '@/components/admin/PersonCell';
import { StatusPill } from '@/components/admin/StatusPill';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SelectField } from '@/components/ui/Field';
import { Td } from '@/components/ui/Table';
import { issueResetLink, updateUser } from '@/lib/api/admin';
import type { UserPatch } from '@/lib/api/admin';
import { describeError } from '@/lib/api/errors';
import { roleSchema } from '@/lib/api/schemas';
import type { ResetLinkResponse, User } from '@/lib/api/schemas';
import type { ResearchUsagePage, UserResearchAllowance } from '@/lib/api/researchUsage';
import { formatUtc } from '@/lib/format';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';

import { roleOptions } from './roleOptions';
import { UserResearchTier } from './UserResearchTier';

export const SELF_MODIFICATION_MESSAGE =
  'You cannot change your own role or active status. Ask another administrator to do it.';

export interface UserRowProps {
  user: User;
  onUpdated: (user: User) => void;
  onResetLink: (response: ResetLinkResponse) => void;
  allowance: UserResearchAllowance | undefined;
  tiers: ResearchUsagePage['tiers'];
  allowanceLoading: boolean;
  onAllowanceUpdated: (value: UserResearchAllowance) => void;
  onAllowanceReload: () => Promise<void>;
}

export function UserRow({
  user,
  onUpdated,
  onResetLink,
  allowance,
  tiers,
  allowanceLoading,
  onAllowanceUpdated,
  onAllowanceReload,
}: UserRowProps) {
  const update = useAsyncAction(async (patch: UserPatch) => {
    onUpdated(await updateUser(user.id, patch));
  });
  const reset = useAsyncAction(async () => {
    onResetLink(await issueResetLink(user.id));
  });
  const busy = update.busy || reset.busy;
  const error = update.error ?? reset.error;
  const message =
    error === null
      ? null
      : error.code === 'self_modification'
        ? SELF_MODIFICATION_MESSAGE
        : describeError(error);
  const options =
    user.role === 'manager'
      ? [{ value: 'manager', label: 'Legacy manager' }, ...roleOptions]
      : roleOptions;

  return (
    <tr>
      <Td className="min-w-56 py-3">
        <PersonCell name={user.display_name} email={user.email} muted={!user.is_active} />
      </Td>
      <Td className="py-3">
        <SelectField
          label={`Role for ${user.email}`}
          labelHidden
          options={options}
          value={user.role}
          disabled={busy}
          className="w-36"
          onChange={(event) => void update.run({ role: roleSchema.parse(event.target.value) })}
        />
      </Td>
      <Td className="py-3">
        <div className="flex flex-col items-start gap-1.5">
          <label className="flex min-h-9 items-center gap-2">
            <input
              type="checkbox"
              checked={user.is_active}
              disabled={busy}
              className="size-4 accent-ember"
              onChange={(event) => void update.run({ is_active: event.target.checked })}
            />
            <span>Active</span>
          </label>
          {user.is_active ? null : <StatusPill tone="neutral">Access paused</StatusPill>}
        </div>
      </Td>
      <Td className="py-3">
        <UserResearchTier
          email={user.email}
          allowance={allowance}
          tiers={tiers}
          loading={allowanceLoading}
          onUpdated={onAllowanceUpdated}
          onReload={onAllowanceReload}
        />
      </Td>
      <Td className="py-3 font-mono text-xs whitespace-nowrap text-muted">
        {user.last_login_at === null ? 'Never' : formatUtc(user.last_login_at)}
      </Td>
      <Td className="min-w-44 py-3">
        <div className="flex flex-col items-start gap-2">
          <Button
            variant="secondary"
            busy={reset.busy}
            disabled={busy}
            onClick={() => void reset.run()}
          >
            Issue reset link
          </Button>
          {message === null ? null : <Alert tone="error">{message}</Alert>}
        </div>
      </Td>
    </tr>
  );
}

import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SelectField } from '@/components/ui/Field';
import { Td } from '@/components/ui/Table';
import { issueResetLink, updateUser } from '@/lib/api/admin';
import type { UserPatch } from '@/lib/api/admin';
import { describeError } from '@/lib/api/errors';
import { roleSchema } from '@/lib/api/schemas';
import type { ResetLinkResponse, User } from '@/lib/api/schemas';
import { formatUtc } from '@/lib/format';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';

import { roleOptions } from './roleOptions';

export const SELF_MODIFICATION_MESSAGE =
  'You cannot change your own role or active status. Ask another administrator to do it.';

export interface UserRowProps {
  user: User;
  onUpdated: (user: User) => void;
  onResetLink: (response: ResetLinkResponse) => void;
}

export function UserRow({ user, onUpdated, onResetLink }: UserRowProps) {
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

  return (
    <tr>
      <Td>
        <div className="font-medium">{user.display_name}</div>
        <div className="text-muted">{user.email}</div>
      </Td>
      <Td>
        <SelectField
          label={`Role for ${user.email}`}
          labelHidden
          options={roleOptions}
          value={user.role}
          disabled={busy}
          className="w-28"
          onChange={(event) => void update.run({ role: roleSchema.parse(event.target.value) })}
        />
      </Td>
      <Td>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={user.is_active}
            disabled={busy}
            className="accent-ember"
            onChange={(event) => void update.run({ is_active: event.target.checked })}
          />
          <span>Active</span>
        </label>
      </Td>
      <Td className="font-mono text-xs whitespace-nowrap">
        {user.last_login_at === null ? 'Never' : formatUtc(user.last_login_at)}
      </Td>
      <Td>
        <div className="flex flex-col gap-2">
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

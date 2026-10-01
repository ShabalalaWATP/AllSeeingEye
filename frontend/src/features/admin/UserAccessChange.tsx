import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import type { Role, User } from '@/lib/api/schemas';

import { roleOptions } from './roleOptions';

/** One proposed change to an account's access, held until an administrator confirms it. */
export type AccessChange = { kind: 'role'; role: Role } | { kind: 'active'; active: boolean };

function roleLabel(role: Role): string {
  if (role === 'manager') return 'Legacy manager';
  return roleOptions.find((option) => option.value === role)?.label ?? role;
}

const accessLabel = (active: boolean) => (active ? 'Active' : 'Paused');

function wording(user: User, change: AccessChange) {
  const name = user.display_name;
  if (change.kind === 'role')
    return {
      title: `Change role for ${name}?`,
      confirm: 'Change role',
      busy: 'Changing role…',
      current: `Current role: ${roleLabel(user.role)}`,
      proposed: `Proposed role: ${roleLabel(change.role)}`,
      effect:
        change.role === 'admin'
          ? 'Admin gives full access to administration, including accounts, teams, sources and model settings, behind a multi-factor verified session.'
          : 'They lose access to administration. Their personal work and team memberships are kept.',
    };
  return change.active
    ? {
        title: `Restore access for ${name}?`,
        confirm: 'Restore access',
        busy: 'Restoring access…',
        current: `Current access: ${accessLabel(user.is_active)}`,
        proposed: `Proposed access: ${accessLabel(true)}`,
        effect:
          'They can sign in again with the access their role and team memberships allow. Earlier activation and reset links stay invalid, so issue a new reset link if they need one.',
      }
    : {
        title: `Pause access for ${name}?`,
        confirm: 'Pause access',
        busy: 'Pausing access…',
        current: `Current access: ${accessLabel(user.is_active)}`,
        proposed: `Proposed access: ${accessLabel(false)}`,
        effect:
          'They cannot sign in, and any outstanding activation or reset link stops working. Their saved work is kept, and access can be restored later.',
      };
}

/**
 * Confirms a role or access change for one account, showing the current and proposed
 * value. The server still decides: a refusal stays in the dialog beside a retry.
 */
export function UserAccessChange({
  user,
  change,
  busy,
  error,
  onConfirm,
  onCancel,
}: {
  user: User;
  change: AccessChange | null;
  busy: boolean;
  error: string | null;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const text = change === null ? null : wording(user, change);
  const caution = change !== null && change.kind === 'active' && !change.active;
  return (
    <ConfirmDialog
      open={text !== null}
      title={text?.title ?? ''}
      confirmLabel={text?.confirm ?? ''}
      busyLabel={text?.busy ?? ''}
      tone={caution ? 'danger' : 'primary'}
      busy={busy}
      error={error}
      onCancel={onCancel}
      onConfirm={onConfirm}
    >
      {text === null ? null : (
        <>
          <p>
            <span className="font-medium text-text">Account:</span> {user.display_name} (
            {user.email})
          </p>
          <ul className="space-y-1">
            <li>{text.current}</li>
            <li className="font-medium text-text">{text.proposed}</li>
          </ul>
          <p>{text.effect}</p>
          {change?.kind === 'active' && change.active ? null : (
            <p>Every session they have open ends, so they must sign in again.</p>
          )}
        </>
      )}
    </ConfirmDialog>
  );
}

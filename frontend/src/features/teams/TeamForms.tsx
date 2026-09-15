import { useState } from 'react';

import { Button } from '@/components/ui/Button';
import { SelectField, TextAreaField, TextField } from '@/components/ui/Field';
import type { MemberInput } from '@/lib/api/teams';

export function TeamNameForm({
  name = '',
  description = '',
  busy,
  onSave,
}: {
  name?: string;
  description?: string | null;
  busy: boolean;
  onSave: (name: string, description?: string) => void;
}) {
  const [value, setValue] = useState(name);
  const [descriptionValue, setDescriptionValue] = useState(description ?? '');
  const trimmedDescription = descriptionValue.trim();
  return (
    <form
      className="flex flex-wrap items-end gap-3"
      aria-label={name ? 'Rename team' : 'Create team'}
      onSubmit={(event) => {
        event.preventDefault();
        if (value.trim()) onSave(value.trim(), trimmedDescription || undefined);
      }}
    >
      <div className="min-w-0 flex-1">
        <TextField
          label={name ? 'Team name' : 'New team name'}
          required
          maxLength={120}
          value={value}
          disabled={busy}
          onChange={(event) => {
            setValue(event.target.value);
          }}
        />
      </div>
      <div className="basis-full">
        <TextAreaField
          label="Team description"
          hint="Optional, up to 500 characters. Explain the workspace's purpose for colleagues."
          maxLength={500}
          rows={2}
          value={descriptionValue}
          disabled={busy}
          onChange={(event) => {
            setDescriptionValue(event.target.value);
          }}
        />
      </div>
      <Button
        type="submit"
        busy={busy}
        disabled={
          !value.trim() ||
          (value.trim() === name && trimmedDescription === (description ?? '').trim())
        }
      >
        {name ? 'Save name' : 'Create team'}
      </Button>
    </form>
  );
}

export function AddMemberForm({
  admin,
  allowManagerRole = admin,
  busy,
  onSave,
}: {
  admin: boolean;
  /** Administrators may add an account directly as a member or manager. */
  allowManagerRole?: boolean;
  busy: boolean;
  onSave: (input: MemberInput) => void;
}) {
  const [email, setEmail] = useState('');
  const [role, setRole] = useState<'member' | 'manager'>('member');
  return (
    <form
      className="grid gap-3 border-t border-line pt-4 sm:grid-cols-[1fr_auto_auto] sm:items-end"
      aria-label="Add team member"
      onSubmit={(event) => {
        event.preventDefault();
        onSave({ email: email.trim(), role });
      }}
    >
      <TextField
        label="Account email"
        type="email"
        autoComplete="off"
        required
        maxLength={320}
        hint="Administrator direct add for an existing active account. The account is added without an invitation."
        value={email}
        disabled={busy}
        onChange={(event) => {
          setEmail(event.target.value);
        }}
      />
      {allowManagerRole ? (
        <SelectField
          label="Team role"
          value={role}
          disabled={busy}
          options={[
            { value: 'member', label: 'Member' },
            { value: 'manager', label: 'Manager' },
          ]}
          onChange={(event) => {
            setRole(event.target.value === 'manager' ? 'manager' : 'member');
          }}
        />
      ) : null}
      <Button type="submit" busy={busy}>
        Add member
      </Button>
      {allowManagerRole ? (
        <p className="text-xs text-muted sm:col-span-3">
          Direct adds are recorded in the audit log. Team managers invite people instead.
        </p>
      ) : null}
    </form>
  );
}

import { useState } from 'react';

import { Button } from '@/components/ui/Button';
import { SelectField, TextField } from '@/components/ui/Field';
import type { MemberInput } from '@/lib/api/teams';

export function TeamNameForm({
  name = '',
  busy,
  onSave,
}: {
  name?: string;
  busy: boolean;
  onSave: (name: string) => void;
}) {
  const [value, setValue] = useState(name);
  return (
    <form
      className="flex flex-wrap items-end gap-3"
      aria-label={name ? 'Rename team' : 'Create team'}
      onSubmit={(event) => {
        event.preventDefault();
        if (value.trim()) onSave(value.trim());
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
      <Button type="submit" busy={busy} disabled={!value.trim() || value.trim() === name}>
        {name ? 'Save name' : 'Create team'}
      </Button>
    </form>
  );
}

export function AddMemberForm({
  admin,
  busy,
  onSave,
}: {
  admin: boolean;
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
        hint="Use an existing active account. No invitation email is sent."
        value={email}
        disabled={busy}
        onChange={(event) => {
          setEmail(event.target.value);
        }}
      />
      {admin ? (
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
      {admin ? (
        <p className="text-xs text-muted sm:col-span-3">
          Team managers must already have a manager or administrator account.
        </p>
      ) : null}
    </form>
  );
}

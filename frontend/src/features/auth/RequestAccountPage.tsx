import { useState } from 'react';
import { Link } from 'react-router';

import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { TextAreaField, TextField } from '@/components/ui/Field';
import { requestAccount } from '@/lib/api/auth';
import { describeError } from '@/lib/api/errors';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';

export function RequestAccountPage() {
  const [email, setEmail] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [reason, setReason] = useState('');
  const [message, setMessage] = useState<string | null>(null);
  const { run, busy, error } = useAsyncAction(async () => {
    const trimmedReason = reason.trim();
    setMessage(
      await requestAccount({
        email,
        display_name: displayName,
        ...(trimmedReason === '' ? {} : { reason: trimmedReason }),
      }),
    );
  });

  if (message !== null) {
    return (
      <div className="flex flex-col gap-4">
        <h1 className="text-lg font-semibold">Request received</h1>
        <Alert tone="success">{message}</Alert>
        <Link to="/login" className="text-sm text-muted hover:text-text">
          Back to sign in
        </Link>
      </div>
    );
  }

  const fieldErrors = error?.code === 'validation_error' ? error.fields : {};

  return (
    <form
      className="flex flex-col gap-4"
      onSubmit={(event) => {
        event.preventDefault();
        void run();
      }}
    >
      <h1 className="text-lg font-semibold">Request an account</h1>
      <p className="text-sm text-muted">
        An administrator reviews every request. You will receive an activation link if it is
        approved.
      </p>
      {error === null || error.code === 'validation_error' ? null : (
        <Alert tone="error">{describeError(error)}</Alert>
      )}
      <TextField
        label="Email"
        name="email"
        type="email"
        autoComplete="email"
        required
        value={email}
        error={fieldErrors.email}
        onChange={(event) => {
          setEmail(event.target.value);
        }}
      />
      <TextField
        label="Display name"
        name="display_name"
        autoComplete="name"
        required
        maxLength={80}
        value={displayName}
        error={fieldErrors.display_name}
        onChange={(event) => {
          setDisplayName(event.target.value);
        }}
      />
      <TextAreaField
        label="Reason (optional)"
        name="reason"
        maxLength={500}
        value={reason}
        error={fieldErrors.reason}
        onChange={(event) => {
          setReason(event.target.value);
        }}
      />
      <Button type="submit" busy={busy}>
        Send request
      </Button>
      <Link to="/login" className="text-sm text-muted hover:text-text">
        Back to sign in
      </Link>
    </form>
  );
}

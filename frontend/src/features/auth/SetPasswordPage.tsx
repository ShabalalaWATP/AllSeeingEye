/**
 * Handles both activation and reset links: `/set-password?token=...`. The token
 * purpose is decided server-side, so the page copy is neutral.
 */
import { useState } from 'react';
import { Link, useSearchParams } from 'react-router';

import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { TextField } from '@/components/ui/Field';
import { setPassword } from '@/lib/api/auth';
import { describeError } from '@/lib/api/errors';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';

import { PASSWORD_MAX, PASSWORD_MIN, PASSWORD_POLICY_TEXT, checkPassword } from './passwordPolicy';

export function SetPasswordPage() {
  const [params] = useSearchParams();
  const token = params.get('token');
  const [password, setPasswordValue] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [localError, setLocalError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const { run, busy, error } = useAsyncAction(async () => {
    await setPassword(token ?? '', password);
    setDone(true);
  });

  if (token === null || token === '') {
    return (
      <div className="flex flex-col gap-4">
        <h1 className="text-lg font-semibold">Link incomplete</h1>
        <Alert tone="error">This link is missing its token. Please request a new one.</Alert>
        <Link to="/forgot-password" className="text-sm text-muted hover:text-text">
          Request a new link
        </Link>
      </div>
    );
  }

  if (done) {
    return (
      <div className="flex flex-col gap-4">
        <h1 className="text-lg font-semibold">Password set</h1>
        <Alert tone="success">Your password has been set. You can sign in now.</Alert>
        <Link to="/login" className="text-sm text-ember hover:underline">
          Go to sign in
        </Link>
      </div>
    );
  }

  const invalidToken = error?.code === 'invalid_token';
  const weakReason = error?.code === 'weak_password' ? error.fieldError('new_password') : undefined;
  const fieldError = localError ?? weakReason;

  return (
    <form
      className="flex flex-col gap-4"
      noValidate
      onSubmit={(event) => {
        event.preventDefault();
        const problem = checkPassword(password, confirmation);
        setLocalError(problem);
        if (problem === null) void run();
      }}
    >
      <h1 className="text-lg font-semibold">Set your password</h1>
      {invalidToken ? (
        <Alert tone="error">
          This link is invalid, has expired or has already been used.{' '}
          <Link to="/forgot-password" className="underline">
            Request a new link
          </Link>
          .
        </Alert>
      ) : null}
      {error !== null && !invalidToken && weakReason === undefined ? (
        <Alert tone="error">{describeError(error)}</Alert>
      ) : null}
      <TextField
        label="New password"
        name="new_password"
        type="password"
        autoComplete="new-password"
        required
        minLength={PASSWORD_MIN}
        maxLength={PASSWORD_MAX}
        hint={PASSWORD_POLICY_TEXT}
        value={password}
        error={fieldError}
        onChange={(event) => {
          setPasswordValue(event.target.value);
        }}
      />
      <TextField
        label="Confirm password"
        name="confirm_password"
        type="password"
        autoComplete="new-password"
        required
        value={confirmation}
        onChange={(event) => {
          setConfirmation(event.target.value);
        }}
      />
      <Button type="submit" busy={busy} disabled={invalidToken}>
        Set password
      </Button>
    </form>
  );
}

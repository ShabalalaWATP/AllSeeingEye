import { useState } from 'react';
import { Link } from 'react-router';

import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { TextField } from '@/components/ui/Field';
import { forgotPassword } from '@/lib/api/auth';
import { describeError } from '@/lib/api/errors';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';

export function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState<string | null>(null);
  const { run, busy, error } = useAsyncAction(async () => {
    setMessage(await forgotPassword(email));
  });

  if (message !== null) {
    return (
      <div className="flex flex-col gap-4">
        <h1 className="text-lg font-semibold">Check your inbox</h1>
        <Alert tone="success">{message}</Alert>
        <Link to="/login" className="text-sm text-muted hover:text-text">
          Back to sign in
        </Link>
      </div>
    );
  }

  return (
    <form
      className="flex flex-col gap-4"
      onSubmit={(event) => {
        event.preventDefault();
        void run();
      }}
    >
      <h1 className="text-lg font-semibold">Forgotten password</h1>
      <p className="text-sm text-muted">
        Enter your email address. If it is registered, a reset link will be issued.
      </p>
      {error === null ? null : <Alert tone="error">{describeError(error)}</Alert>}
      <TextField
        label="Email"
        name="email"
        type="email"
        autoComplete="email"
        required
        value={email}
        error={error?.code === 'validation_error' ? error.fieldError('email') : undefined}
        onChange={(event) => {
          setEmail(event.target.value);
        }}
      />
      <Button type="submit" busy={busy}>
        Send reset link
      </Button>
      <Link to="/login" className="text-sm text-muted hover:text-text">
        Back to sign in
      </Link>
    </form>
  );
}

import { useState } from 'react';
import { Link, Navigate, useLocation } from 'react-router';

import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { TextField } from '@/components/ui/Field';
import { describeError } from '@/lib/api/errors';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';
import { useAuthStore } from '@/stores/auth';

import { redirectTarget } from './redirect';

export function LoginPage() {
  const location = useLocation();
  const status = useAuthStore((state) => state.status);
  const login = useAuthStore((state) => state.login);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const { run, busy, error } = useAsyncAction(() => login(email, password));

  const destination = redirectTarget(location.state);
  if (status === 'authenticated') {
    return <Navigate to={destination} replace />;
  }

  return (
    <form
      className="flex flex-col gap-4"
      onSubmit={(event) => {
        event.preventDefault();
        void run();
      }}
    >
      <h1 className="text-lg font-semibold">Sign in</h1>
      {error === null ? null : <Alert tone="error">{describeError(error)}</Alert>}
      <TextField
        label="Email"
        name="email"
        type="email"
        autoComplete="email"
        required
        value={email}
        onChange={(event) => {
          setEmail(event.target.value);
        }}
      />
      <TextField
        label="Password"
        name="password"
        type="password"
        autoComplete="current-password"
        required
        value={password}
        onChange={(event) => {
          setPassword(event.target.value);
        }}
      />
      <Button type="submit" busy={busy}>
        Sign in
      </Button>
      <nav aria-label="Account help" className="flex justify-between text-sm text-muted">
        <Link to="/request-account" className="hover:text-text">
          Request an account
        </Link>
        <Link to="/forgot-password" className="hover:text-text">
          Forgotten password
        </Link>
      </nav>
    </form>
  );
}

import { useState } from 'react';
import { Link, Navigate, useLocation } from 'react-router';

import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { TextField } from '@/components/ui/Field';
import type { PendingMfa } from '@/lib/api/mfa';
import { describeError } from '@/lib/api/errors';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';
import { selectIsAdmin, useAuthStore } from '@/stores/auth';

import { MfaLoginStep } from './MfaLoginStep';
import { redirectTarget } from './redirect';

export function LoginPage() {
  const location = useLocation();
  const status = useAuthStore((state) => state.status);
  const login = useAuthStore((state) => state.login);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [challenge, setChallenge] = useState<PendingMfa | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const [capsLock, setCapsLock] = useState(false);
  const { run, busy, error } = useAsyncAction(async () => {
    const pending = await login(email, password);
    setPassword('');
    setShowPassword(false);
    setChallenge(pending);
  });

  const isAdmin = useAuthStore(selectIsAdmin);
  const destination = redirectTarget(location.state, isAdmin ? '/admin' : '/');
  const state: unknown = location.state;
  const passwordChanged =
    typeof state === 'object' &&
    state !== null &&
    'passwordChanged' in state &&
    state.passwordChanged === true;
  if (status === 'authenticated') {
    return <Navigate to={destination} replace />;
  }

  if (challenge !== null) {
    return (
      <MfaLoginStep
        challenge={challenge}
        onBack={() => {
          setChallenge(null);
        }}
      />
    );
  }

  return (
    <form
      className="flex flex-col gap-5"
      aria-busy={busy}
      onSubmit={(event) => {
        event.preventDefault();
        if (!busy) void run();
      }}
    >
      <header className="mb-2">
        <p className="mb-3 font-mono text-xs uppercase tracking-widest text-muted">
          Account access
        </p>
        <h1 className="text-3xl font-semibold tracking-tight">Sign in</h1>
        <p className="mt-3 text-sm leading-relaxed text-muted">
          Use your approved account to continue.
        </p>
      </header>
      {error === null ? null : <Alert tone="error">{describeError(error)}</Alert>}
      {passwordChanged ? (
        <Alert tone="success">Your password has changed. Sign in with your new password.</Alert>
      ) : null}
      <TextField
        label="Email"
        name="email"
        type="email"
        autoComplete="email"
        required
        disabled={busy}
        className="min-h-12"
        value={email}
        onChange={(event) => {
          setEmail(event.target.value);
        }}
      />
      <div className="relative">
        <TextField
          label="Password"
          name="password"
          type={showPassword ? 'text' : 'password'}
          autoComplete="current-password"
          required
          disabled={busy}
          className="min-h-12 pr-20"
          value={password}
          onKeyUp={(event) => {
            setCapsLock(event.getModifierState('CapsLock'));
          }}
          onKeyDown={(event) => {
            setCapsLock(event.getModifierState('CapsLock'));
          }}
          onBlur={() => {
            setCapsLock(false);
          }}
          onChange={(event) => {
            setPassword(event.target.value);
          }}
        />
        <button
          type="button"
          className="absolute right-1 top-7 min-h-11 min-w-16 rounded px-3 text-xs font-medium text-muted hover:text-text"
          aria-label={showPassword ? 'Hide password' : 'Show password'}
          aria-pressed={showPassword}
          disabled={busy}
          onClick={() => {
            setShowPassword((shown) => !shown);
          }}
        >
          {showPassword ? 'Hide' : 'Show'}
        </button>
        {capsLock ? (
          <p role="status" className="mt-2 text-xs text-ember">
            Caps Lock is on.
          </p>
        ) : null}
      </div>
      <Button type="submit" busy={busy} className="min-h-12">
        {busy ? 'Signing in…' : 'Sign in'}
      </Button>
      <nav
        aria-label="Account help"
        className="mt-2 flex flex-wrap justify-between gap-x-5 gap-y-2 border-t border-line pt-5 text-sm text-muted"
      >
        <Link to="/request-account" className="rounded py-2 hover:text-text">
          Request an account
        </Link>
        <Link to="/forgot-password" className="rounded py-2 hover:text-text">
          Forgotten password
        </Link>
      </nav>
    </form>
  );
}

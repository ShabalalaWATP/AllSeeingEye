import { useRef, useState } from 'react';
import { flushSync } from 'react-dom';
import { useNavigate } from 'react-router';

import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { TextField } from '@/components/ui/Field';
import { changePassword } from '@/lib/api/account';
import { describeError } from '@/lib/api/errors';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';
import {
  checkPassword,
  PASSWORD_MAX,
  PASSWORD_MIN,
  PASSWORD_POLICY_TEXT,
} from '@/lib/passwordPolicy';
import { useAuthStore } from '@/stores/auth';

export function ChangePasswordForm({ actorId }: { actorId: string }) {
  const navigate = useNavigate();
  const [current, setCurrent] = useState('');
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [code, setCode] = useState('');
  const [visible, setVisible] = useState(false);
  const [validation, setValidation] = useState<string | null>(null);
  const inFlight = useRef(false);
  const action = useAsyncAction(async () => {
    if (inFlight.current) return;
    inFlight.current = true;
    try {
      await changePassword({
        current_password: current,
        new_password: password,
        totp_code: code || null,
      });
      // A response for an earlier identity must not sign out a newly signed-in account.
      if (useAuthStore.getState().user?.id === actorId) {
        // Commit the auth guard's sign-out before replacing its redirect with the notice.
        flushSync(() => useAuthStore.getState().clearSession());
        await navigate('/login', { replace: true, state: { passwordChanged: true } });
      }
    } finally {
      inFlight.current = false;
    }
  });
  const error =
    validation ??
    (action.error?.code === 'weak_password' ? action.error.fieldError('new_password') : null);
  return (
    <form
      aria-label="Change password"
      aria-busy={action.busy}
      noValidate
      className="flex flex-col gap-5"
      onSubmit={(event) => {
        event.preventDefault();
        if (action.busy || inFlight.current) return;
        const problem =
          current === ''
            ? 'Enter your current password.'
            : (checkPassword(password, confirmation) ??
              (code !== '' && !/^[0-9]{6}$/.test(code)
                ? 'Enter a six-digit authenticator code, or leave it blank if none is enabled.'
                : null));
        setValidation(problem);
        if (problem === null) void action.run();
      }}
    >
      <header>
        <h2 className="text-xl font-semibold">Change password</h2>
        <p className="mt-2 text-sm leading-relaxed text-muted">
          Changing your password signs you out on every device. Sign in again with the new password.
        </p>
      </header>
      {error ? <Alert tone="error">{error}</Alert> : null}
      {action.error &&
      !(action.error.code === 'weak_password' && action.error.fieldError('new_password')) ? (
        <Alert tone="error">{describeError(action.error)}</Alert>
      ) : null}
      <fieldset disabled={action.busy} className="flex min-w-0 flex-col gap-4">
        <legend className="sr-only">Password details</legend>
        <TextField
          label="Current password"
          name="current_password"
          type={visible ? 'text' : 'password'}
          autoComplete="current-password"
          required
          value={current}
          className="min-h-11"
          onChange={(event) => setCurrent(event.target.value)}
        />
        <TextField
          label="New password"
          name="new_password"
          type={visible ? 'text' : 'password'}
          autoComplete="new-password"
          minLength={PASSWORD_MIN}
          maxLength={PASSWORD_MAX}
          hint={PASSWORD_POLICY_TEXT}
          required
          value={password}
          className="min-h-11"
          onChange={(event) => setPassword(event.target.value)}
        />
        <TextField
          label="Confirm new password"
          name="confirm_password"
          type={visible ? 'text' : 'password'}
          autoComplete="new-password"
          required
          value={confirmation}
          className="min-h-11"
          onChange={(event) => setConfirmation(event.target.value)}
        />
        <button
          type="button"
          aria-pressed={visible}
          className="min-h-11 w-fit rounded text-sm text-muted hover:text-text"
          onClick={() => setVisible((value) => !value)}
        >
          {visible ? 'Hide passwords' : 'Show passwords'}
        </button>
        <details>
          <summary className="min-h-11 w-fit cursor-pointer rounded py-3 text-sm text-muted hover:text-text">
            Use an authenticator code
          </summary>
          <TextField
            label="Authenticator code"
            name="totp_code"
            hint="Required if an authenticator is enabled for your account."
            inputMode="numeric"
            autoComplete="one-time-code"
            maxLength={6}
            value={code}
            className="min-h-11 font-mono tracking-widest"
            onChange={(event) => setCode(event.target.value)}
          />
        </details>
      </fieldset>
      <Button type="submit" busy={action.busy} className="min-h-11 self-start">
        {action.busy ? 'Changing password…' : 'Change password'}
      </Button>
    </form>
  );
}

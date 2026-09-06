import { useEffect, useRef } from 'react';

import { AuthenticatorQr } from '@/components/account/AuthenticatorQr';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { TextField } from '@/components/ui/Field';
import { describeError } from '@/lib/api/errors';
import type { PendingMfa } from '@/lib/api/mfa';

import { useMfaLogin } from './useMfaLogin';

export function MfaLoginStep({ challenge, onBack }: { challenge: PendingMfa; onBack: () => void }) {
  const mfa = useMfaLogin(challenge);
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    heading.current?.focus();
  }, []);
  const isApp = mfa.method === 'authenticator';
  const isRecovery = mfa.method === 'recovery';
  const ready =
    isRecovery ||
    (isApp ? !challenge.enrollment_required || mfa.enrolment !== null : mfa.emailSent);

  return (
    <form
      className="flex flex-col gap-5"
      aria-busy={mfa.busy}
      onSubmit={(event) => {
        event.preventDefault();
        if (!mfa.busy && ready) void mfa.run('verify');
      }}
    >
      <header className="mb-2">
        <p className="mb-3 font-mono text-xs uppercase tracking-widest text-muted">
          Account security
        </p>
        <h1 ref={heading} tabIndex={-1} className="text-3xl font-semibold tracking-tight">
          {challenge.enrollment_required ? 'Secure your account' : 'Verify your sign-in'}
        </h1>
        <p className="mt-3 text-sm leading-relaxed text-muted">
          {challenge.enrollment_required
            ? 'Administrators must enable multi-factor authentication before continuing. Choose a method to get started.'
            : 'Your password is verified. Complete the security check to continue.'}
        </p>
      </header>
      {mfa.error === null ? null : (
        <Alert tone="error">
          {mfa.error.code === 'invalid_credentials'
            ? 'The code or sign-in request is invalid or has expired. Try a fresh code, or return to sign in.'
            : describeError(mfa.error)}
        </Alert>
      )}
      {challenge.methods.length > 1 ? (
        <div className="flex flex-wrap gap-2" role="group" aria-label="Verification method">
          {challenge.methods.map((method) => (
            <Button
              key={method}
              variant={mfa.method === method ? 'secondary' : 'ghost'}
              aria-pressed={mfa.method === method}
              disabled={mfa.busy}
              onClick={() => {
                mfa.chooseMethod(method);
              }}
            >
              {method === 'authenticator'
                ? 'Authenticator app'
                : method === 'email'
                  ? 'Email code'
                  : 'Recovery code'}
            </Button>
          ))}
        </div>
      ) : null}
      {isApp && challenge.enrollment_required ? (
        <section className="space-y-3 border-y border-line py-4" aria-label="Authenticator setup">
          <p className="text-sm text-muted">
            Scan the QR code or enter the setup key in your authenticator app, then enter its
            six-digit code.
          </p>
          {mfa.enrolment === null ? (
            <Button
              variant="secondary"
              busy={mfa.busy}
              onClick={() => {
                void mfa.run('app');
              }}
            >
              Set up authenticator app
            </Button>
          ) : (
            <div className="space-y-3">
              <AuthenticatorQr uri={mfa.enrolment.provisioning_uri} />
              <p className="mb-2 text-xs text-muted">Setup key</p>
              <code className="block select-all break-all rounded bg-surface-2 p-3 font-mono text-sm tracking-wider">
                {mfa.enrolment.secret}
              </code>
              <p className="mt-2 text-xs text-muted">
                Keep this key private. Choose a time-based account in your app.
              </p>
            </div>
          )}
        </section>
      ) : null}
      {mfa.method === 'email' ? (
        <div className="space-y-3">
          <p className="text-sm text-muted" role="status">
            {mfa.emailSent
              ? 'A verification code has been sent to your account email.'
              : 'Send a verification code to your account email.'}
          </p>
          <Button
            variant="secondary"
            busy={mfa.busy}
            onClick={() => {
              void mfa.run('email');
            }}
          >
            {mfa.emailSent ? 'Send a new code' : 'Send email code'}
          </Button>
        </div>
      ) : null}
      {ready ? (
        <>
          <TextField
            label={
              isRecovery
                ? 'Recovery code'
                : isApp
                  ? 'Authenticator code'
                  : 'Email verification code'
            }
            name="mfa_code"
            hint={
              isRecovery
                ? 'Enter one unused recovery code. Each code works once.'
                : isApp
                  ? 'Enter the current six-digit code from your app.'
                  : 'Enter the most recent six-digit code from your email.'
            }
            inputMode={isRecovery ? 'text' : 'numeric'}
            autoComplete={isRecovery ? 'off' : 'one-time-code'}
            pattern={isRecovery ? '(?:[A-Fa-f0-9]|-){32,39}' : '[0-9]{6}'}
            maxLength={isRecovery ? 39 : 6}
            required
            disabled={mfa.busy}
            className="min-h-12 font-mono tracking-widest"
            value={mfa.code}
            onChange={(event) => {
              mfa.setCode(event.target.value);
            }}
          />
          <Button type="submit" busy={mfa.busy} className="min-h-12">
            {mfa.busy
              ? 'Verifying...'
              : challenge.enrollment_required
                ? 'Enable MFA and continue'
                : 'Verify and sign in'}
          </Button>
        </>
      ) : null}
      <Button variant="ghost" disabled={mfa.busy} onClick={onBack}>
        Back to sign in
      </Button>
    </form>
  );
}

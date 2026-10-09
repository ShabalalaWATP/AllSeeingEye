import { useEffect, useRef } from 'react';

import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { TextField } from '@/components/ui/Field';
import { PageHeader } from '@/components/ui/PageHeader';
import { describeError } from '@/lib/api/errors';
import type { PendingMfa } from '@/lib/api/mfa';

import { AuthenticatorEnrolment } from './AuthenticatorEnrolment';
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
        if (ready) void mfa.run('verify');
      }}
    >
      <PageHeader
        className="mb-2"
        title={challenge.enrollment_required ? 'Secure your account' : 'Verify your sign-in'}
        headingRef={heading}
        focusable
        eyebrow="Account security"
        eyebrowTone="muted"
        description={
          challenge.enrollment_required
            ? 'Administrators must enable multi-factor authentication before continuing. Choose a method to get started.'
            : 'Your password is verified. Complete the security check to continue.'
        }
      />
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
        <AuthenticatorEnrolment
          enrolment={mfa.enrolment}
          emailProofRequired={challenge.authenticator_email_proof}
          emailSent={mfa.emailSent}
          emailProof={mfa.emailProof}
          busy={mfa.busy}
          onEmailProofChange={mfa.setEmailProof}
          onSendEmail={() => {
            void mfa.run('email');
          }}
          onSetUp={() => {
            void mfa.run('app');
          }}
        />
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

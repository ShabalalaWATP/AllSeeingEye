import { lazy, Suspense } from 'react';

import { Button } from '@/components/ui/Button';
import { TextField } from '@/components/ui/Field';
import type { MfaEnrolment } from '@/lib/api/mfa';

// The QR encoder is only needed during authenticator enrolment, so keep it out of the entry chunk.
const AuthenticatorQr = lazy(async () => {
  const module = await import('@/components/account/AuthenticatorQr');
  return { default: module.AuthenticatorQr };
});

interface Props {
  enrolment: MfaEnrolment | null;
  /** Whether the account address must be confirmed before the setup key is issued. */
  emailProofRequired: boolean;
  emailSent: boolean;
  emailProof: string;
  busy: boolean;
  onEmailProofChange: (value: string) => void;
  onSendEmail: () => void;
  onSetUp: () => void;
}

export function AuthenticatorEnrolment({
  enrolment,
  emailProofRequired,
  emailSent,
  emailProof,
  busy,
  onEmailProofChange,
  onSendEmail,
  onSetUp,
}: Props) {
  if (enrolment !== null) {
    return (
      <section className="space-y-3 border-y border-line py-4" aria-label="Authenticator setup">
        <p className="text-sm text-muted">
          Scan the QR code or enter the setup key in your authenticator app, then enter its
          six-digit code.
        </p>
        <div className="space-y-3">
          <Suspense
            fallback={
              <p role="status" className="flex h-52 w-52 items-center text-sm text-muted">
                Preparing QR code...
              </p>
            }
          >
            <AuthenticatorQr uri={enrolment.provisioning_uri} />
          </Suspense>
          <p className="mb-2 text-xs text-muted">Setup key</p>
          <code className="block select-all break-all rounded bg-surface-2 p-3 font-mono text-sm tracking-wider">
            {enrolment.secret}
          </code>
          <p className="mt-2 text-xs text-muted">
            Keep this key private. Choose a time-based account in your app.
          </p>
        </div>
      </section>
    );
  }
  const proofReady = /^[0-9]{6}$/.test(emailProof);
  return (
    <section className="space-y-3 border-y border-line py-4" aria-label="Authenticator setup">
      {emailProofRequired ? (
        <>
          <p className="text-sm text-muted" role="status">
            {emailSent
              ? 'A confirmation code has been sent to your account email. Enter it to set up your authenticator app.'
              : 'Before setting up an authenticator app, confirm a code sent to your account email.'}
          </p>
          <Button variant="secondary" busy={busy} onClick={onSendEmail}>
            {emailSent ? 'Send a new code' : 'Send email code'}
          </Button>
          {emailSent ? (
            <TextField
              label="Email confirmation code"
              name="mfa_enrol_email_code"
              hint="Enter the most recent six-digit code from your email."
              inputMode="numeric"
              autoComplete="one-time-code"
              pattern="[0-9]{6}"
              maxLength={6}
              className="min-h-12 font-mono tracking-widest"
              value={emailProof}
              onChange={(event) => {
                onEmailProofChange(event.target.value);
              }}
            />
          ) : null}
        </>
      ) : (
        <p className="text-sm text-muted">
          Scan the QR code or enter the setup key in your authenticator app, then enter its
          six-digit code.
        </p>
      )}
      {emailProofRequired && !emailSent ? null : (
        <Button
          variant="secondary"
          busy={busy}
          disabled={emailProofRequired && !proofReady}
          onClick={onSetUp}
        >
          Set up authenticator app
        </Button>
      )}
    </section>
  );
}

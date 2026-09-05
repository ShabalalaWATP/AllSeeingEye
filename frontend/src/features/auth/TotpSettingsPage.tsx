import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { TextField } from '@/components/ui/Field';
import { describeError } from '@/lib/api/errors';

import { useTotpSettings } from './useTotpSettings';

export function TotpSettingsPage() {
  const { resource, enrolment, password, setPassword, code, setCode, action, restart } =
    useTotpSettings();
  const enabled = resource.data?.enabled ?? false;
  return (
    <section className="mx-auto flex max-w-xl flex-col gap-5 p-6" aria-labelledby="totp-title">
      <h1 id="totp-title" className="text-xl font-semibold">
        Administrator security
      </h1>
      <p className="text-sm text-muted">
        Protect sign-in with a six-digit code from your authenticator app. Enabling or disabling
        TOTP signs you out and revokes every refresh session.
      </p>
      {resource.loading ? <p role="status">Loading second-factor settings...</p> : null}
      {resource.error !== null ? <Alert tone="error">{describeError(resource.error)}</Alert> : null}
      {resource.data !== null ? (
        <>
          <p role="status">TOTP is {enabled ? 'enabled' : 'disabled'}.</p>
          {!resource.data.available ? (
            <Alert tone="warning">
              The server encryption key must be configured to manage TOTP.
            </Alert>
          ) : (
            <form
              className="flex flex-col gap-4"
              onSubmit={(event) => {
                event.preventDefault();
                void action.run();
              }}
            >
              {action.error !== null ? (
                <Alert tone="error">{describeError(action.error)}</Alert>
              ) : null}
              {enrolment === null ? (
                <TextField
                  label="Current password"
                  type="password"
                  required
                  autoComplete="current-password"
                  value={password}
                  onChange={(event) => {
                    setPassword(event.target.value);
                  }}
                />
              ) : (
                <div className="flex flex-col gap-3 text-sm">
                  <p>
                    Add a time-based account named The All Seeing Eye in your authenticator app.
                    Enter this setup key, then confirm its code within ten minutes.
                  </p>
                  <TextField
                    label="Authenticator setup key"
                    value={enrolment.secret}
                    readOnly
                    autoComplete="off"
                  />
                  <p className="text-muted">
                    Keep this key private. It is shown only during enrolment. After confirming, wait
                    for a new code before signing in again.
                  </p>
                </div>
              )}
              {enabled || enrolment !== null ? (
                <TextField
                  label="Authenticator code"
                  required
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  pattern="[0-9]{6}"
                  maxLength={6}
                  value={code}
                  onChange={(event) => {
                    setCode(event.target.value);
                  }}
                />
              ) : null}
              <Button type="submit" busy={action.busy}>
                {enabled
                  ? 'Disable TOTP'
                  : enrolment !== null
                    ? 'Confirm and enable TOTP'
                    : 'Set up TOTP'}
              </Button>
              {enrolment !== null ? (
                <Button type="button" variant="secondary" disabled={action.busy} onClick={restart}>
                  Restart setup
                </Button>
              ) : null}
            </form>
          )}
          <p className="text-xs text-muted">
            Lost your authenticator? The host operator can use the local administrator recovery
            command with your current password. Password resets do not remove TOTP.
          </p>
        </>
      ) : null}
    </section>
  );
}

export default TotpSettingsPage;

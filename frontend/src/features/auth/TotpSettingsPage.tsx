import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { TextField } from '@/components/ui/Field';
import { describeError } from '@/lib/api/errors';

import { useTotpSettings } from './useTotpSettings';

export function TotpSettingsPage() {
  const state = useTotpSettings();
  const {
    resource,
    method,
    enabled,
    enrolment,
    challenge,
    password,
    setPassword,
    code,
    setCode,
    action,
    restart,
  } = state;
  const status = resource.data;
  const confirming = enrolment !== null || challenge !== null;
  return (
    <section className="h-full overflow-y-auto p-4 sm:p-6" aria-labelledby="mfa-title">
      <div className="mx-auto flex max-w-2xl flex-col gap-6">
        <header>
          <p className="font-mono text-xs uppercase tracking-widest text-muted">
            Personal security
          </p>
          <h1 id="mfa-title" className="mt-2 text-2xl font-semibold">
            Multi-factor authentication
          </h1>
          <p className="mt-3 text-sm leading-relaxed text-muted">
            Add a second check after your password. Choose an authenticator app, email codes, or
            both.
          </p>
        </header>
        {resource.loading ? <p role="status">Loading security settings...</p> : null}
        {resource.error !== null ? (
          <Alert tone="error">{describeError(resource.error)}</Alert>
        ) : null}
        {status !== null ? (
          <>
            {status.required ? (
              <Alert>
                Administrator accounts must keep at least one verification method enabled.
              </Alert>
            ) : null}
            <div className="divide-y divide-line border-y border-line">
              {(['authenticator', 'email'] as const).map((option) => {
                const active = status.methods.includes(option);
                const available = status.available_methods.includes(option);
                const lastRequired =
                  active && status.required && status.methods.length === 1;
                const title =
                  option === 'authenticator' ? 'Authenticator app' : 'Email verification';
                return (
                  <article
                    key={option}
                    className="flex flex-wrap items-center justify-between gap-4 py-5"
                  >
                    <div className="max-w-md">
                      <h2 className="font-semibold">{title}</h2>
                      <p className="mt-1 text-sm text-muted">
                        {option === 'authenticator'
                          ? 'Use a six-digit, time-based code from your authenticator app.'
                          : 'Receive a one-time code at your account email address.'}
                      </p>
                      <p className="mt-2 text-xs text-muted">
                        {active
                          ? 'Enabled'
                          : available
                            ? 'Not enabled'
                            : 'Unavailable. Contact your administrator.'}
                        {lastRequired ? ' · Enable another method before removing this one.' : ''}
                      </p>
                    </div>
                    <Button
                      type="button"
                      variant="secondary"
                      disabled={!available || lastRequired || method !== null}
                      onClick={() => state.setMethod(option)}
                    >
                      {active ? `Disable ${title.toLowerCase()}` : `Set up ${title.toLowerCase()}`}
                    </Button>
                  </article>
                );
              })}
            </div>
            {method !== null ? (
              <form
                className="flex flex-col gap-4 rounded-lg border border-line p-5"
                aria-label={`${enabled ? 'Disable' : 'Set up'} ${method}`}
                onSubmit={(event) => {
                  event.preventDefault();
                  void action.run();
                }}
              >
                <h2 className="font-semibold">
                  {enabled ? 'Confirm removal' : 'Verify your new method'}
                </h2>
                {action.error !== null ? (
                  <Alert tone="error">{describeError(action.error)}</Alert>
                ) : null}
                <fieldset disabled={action.busy} className="flex min-w-0 flex-col gap-4">
                  {!confirming ? (
                    <TextField
                      label="Current password"
                      type="password"
                      required
                      autoComplete="current-password"
                      value={password}
                      onChange={(event) => setPassword(event.target.value)}
                    />
                  ) : null}
                  {enrolment !== null ? (
                    <>
                      <p className="text-sm text-muted">
                        Add a time-based account named The All Seeing Eye in your authenticator app.
                        Enter this setup key, then confirm its code within ten minutes.
                      </p>
                      <TextField
                        label="Authenticator setup key"
                        value={enrolment.secret}
                        readOnly
                        autoComplete="off"
                      />
                      <p className="text-xs text-muted">
                        Keep this key private. After confirming, wait for a new code before signing
                        in again.
                      </p>
                    </>
                  ) : null}
                  {challenge !== null ? (
                    <p role="status" className="text-sm text-muted">
                      A verification code has been sent to your account email address.
                    </p>
                  ) : null}
                  {confirming || (method === 'authenticator' && enabled) ? (
                    <TextField
                      label={method === 'email' ? 'Email verification code' : 'Authenticator code'}
                      required
                      inputMode="numeric"
                      autoComplete="one-time-code"
                      pattern="[0-9]{6}"
                      maxLength={6}
                      value={code}
                      onChange={(event) => setCode(event.target.value)}
                    />
                  ) : null}
                </fieldset>
                <div className="flex flex-wrap gap-3">
                  <Button type="submit" busy={action.busy}>
                    {method === 'email' && !confirming
                      ? 'Send verification code'
                      : enabled
                        ? 'Confirm and disable'
                        : confirming
                          ? 'Confirm and enable'
                          : 'Continue setup'}
                  </Button>
                  <Button
                    type="button"
                    variant="secondary"
                    disabled={action.busy}
                    onClick={restart}
                  >
                    Cancel
                  </Button>
                </div>
              </form>
            ) : null}
            <p className="text-xs leading-relaxed text-muted">
              Enabling or disabling a method signs you out on every device. Sign in again to
              continue. Password resets keep your verification methods enabled.
            </p>
          </>
        ) : null}
      </div>
    </section>
  );
}
export default TotpSettingsPage;

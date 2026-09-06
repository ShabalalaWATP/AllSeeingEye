import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { TextField } from '@/components/ui/Field';
import type { RecoveryStatus } from '@/lib/api/accountSecurity';
import { describeError } from '@/lib/api/errors';
import { saveTextFile } from '@/lib/download';
import { useRecoveryCodes } from './useRecoveryCodes';

export function RecoveryCodes({
  status,
  methods,
  onChanged,
}: {
  status: RecoveryStatus;
  methods: readonly string[];
  onChanged: () => Promise<void>;
}) {
  const state = useRecoveryCodes(methods, onChanged);
  return (
    <section className="space-y-4 border-t border-line pt-6" aria-labelledby="recovery-title">
      <h2 id="recovery-title" className="text-xl font-semibold">
        Recovery codes
      </h2>
      <p className="text-sm text-muted">
        Use a single-use recovery code after your password if your usual MFA method is unavailable.
        Keep them somewhere private and separate from this device.
      </p>
      <p className="text-sm">
        {status.available
          ? `${status.remaining} unused codes available`
          : 'Enable MFA before creating recovery codes.'}
      </p>
      <p className="text-xs text-muted">
        Password resets, password changes and MFA changes invalidate these codes. They do not
        replace your enabled MFA method.
      </p>
      {state.codes.length > 0 ? (
        <div className="space-y-4 rounded border border-line p-4">
          <Alert>
            These codes are shown only once. Any previous recovery codes are now invalid.
          </Alert>
          <ol
            className="grid gap-2 font-mono text-xs sm:grid-cols-2"
            aria-label="New recovery codes"
          >
            {state.codes.map((code) => (
              <li className="select-all break-all" key={code}>
                {code.match(/.{1,4}/g)?.join('-')}
              </li>
            ))}
          </ol>
          <div className="flex flex-wrap gap-3">
            <Button
              variant="secondary"
              onClick={() =>
                saveTextFile(
                  'ase-recovery-codes.txt',
                  `The All Seeing Eye recovery codes
Keep these private. Each code works once.

${state.codes.join('\n')}
`,
                )
              }
            >
              Download recovery codes
            </Button>
            <Button onClick={() => state.setCodes([])}>I have saved my codes</Button>
          </div>
        </div>
      ) : null}
      {!state.open && state.codes.length === 0 && (
        <Button
          variant="secondary"
          disabled={!status.available}
          onClick={() => state.setOpen(true)}
        >
          {status.remaining ? 'Replace recovery codes' : 'Create recovery codes'}
        </Button>
      )}
      {state.open && (
        <form
          className="space-y-4 rounded border border-line p-4"
          aria-label="Create recovery codes"
          onSubmit={(event) => {
            event.preventDefault();
            if (!state.action.busy) void state.action.run();
          }}
        >
          {state.action.error && <Alert tone="error">{describeError(state.action.error)}</Alert>}
          {status.remaining > 0 && (
            <Alert>Creating a new set immediately invalidates your previous codes.</Alert>
          )}
          <fieldset disabled={state.action.busy} className="space-y-4">
            <TextField
              label="Current password for recovery codes"
              type="password"
              required
              autoComplete="current-password"
              value={state.password}
              onChange={(event) => {
                state.setPassword(event.target.value);
                state.setChallenge(null);
              }}
            />
            {methods.includes('authenticator') && methods.includes('email') && (
              <div
                className="flex flex-wrap gap-2"
                role="group"
                aria-label="Recovery code verification method"
              >
                <Button
                  variant="secondary"
                  aria-pressed={state.method === 'authenticator'}
                  onClick={() => state.changeMethod('authenticator')}
                >
                  Authenticator app
                </Button>
                <Button
                  variant="secondary"
                  aria-pressed={state.method === 'email'}
                  onClick={() => state.changeMethod('email')}
                >
                  Email verification
                </Button>
              </div>
            )}
            {state.challenge && (
              <p role="status" className="text-sm text-muted">
                Enter the verification code sent to your account email.
              </p>
            )}
            {(state.method === 'authenticator' || state.challenge !== null) && (
              <TextField
                label={
                  state.method === 'authenticator'
                    ? 'Authenticator code for recovery codes'
                    : 'Email code for recovery codes'
                }
                required
                inputMode="numeric"
                pattern="[0-9]{6}"
                maxLength={6}
                autoComplete="one-time-code"
                value={state.code}
                onChange={(event) => state.setCode(event.target.value)}
              />
            )}
          </fieldset>
          <div className="flex gap-3">
            <Button type="submit" busy={state.action.busy}>
              {state.method === 'email' && !state.challenge
                ? 'Send verification email'
                : 'Generate new codes'}
            </Button>
            <Button variant="ghost" disabled={state.action.busy} onClick={state.reset}>
              Cancel
            </Button>
          </div>
        </form>
      )}
    </section>
  );
}

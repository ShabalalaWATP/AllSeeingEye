import { useState } from 'react';
import { AdminIcon } from '@/components/admin/AdminIcon';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { TextField } from '@/components/ui/Field';
import { useFirmsConnection } from './useFirmsConnection';

export function FirmsConnectionPanel() {
  const [open, setOpen] = useState(false);
  return (
    <section
      className="admin-rise rounded-card border border-line/80 bg-surface/70 px-4 py-4 sm:px-5"
      aria-label="NASA FIRMS connection"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex min-w-0 items-start gap-3">
          <span className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg border border-line/80 bg-surface-2 text-ember">
            <AdminIcon name="key" size={16} />
          </span>
          <div className="min-w-0">
            <h2 className="font-semibold">NASA FIRMS</h2>
            <p className="mt-1 text-xs text-muted">
              NOAA-20 VIIRS thermal observations · Optional Area API connection
            </p>
          </div>
        </div>
        <Button variant="secondary" aria-expanded={open} onClick={() => setOpen(!open)}>
          {open ? 'Close FIRMS connection' : 'Manage FIRMS connection'}
        </Button>
      </div>
      {open && <FirmsConnectionJourney />}
    </section>
  );
}

function FirmsConnectionJourney() {
  const connection = useFirmsConnection();
  const { status, busy, run } = connection;
  const editable =
    status?.credential_origin !== 'environment' &&
    status?.encryption_available &&
    !status.environment_disabled;
  return (
    <div className="mt-5 space-y-4" aria-label="FIRMS connection settings">
      <p className="max-w-3xl text-sm text-muted">
        Public NOAA-20 downloads work without a key. This optional Area API connection serves every
        user and team. Test a private draft, then confirm it for the next scheduled poll. Enabling
        the source and displaying FIRMS on the map are separate controls.
      </p>
      <p className="max-w-3xl text-sm text-muted">
        Need a key?{' '}
        <a
          href="https://firms.modaps.eosdis.nasa.gov/api/area/"
          target="_blank"
          rel="noopener noreferrer"
          className="text-cyan underline underline-offset-4"
        >
          Request a free MAP_KEY from NASA FIRMS
        </a>
        . NASA sends the key to your email address. Return here to test and confirm it. Turning on
        the map layer alone does not activate this optional keyed connection.
      </p>
      {connection.error && <Alert tone="error">{connection.error}</Alert>}
      {connection.notice && (
        <p role="status" className="text-sm">
          {connection.notice}
        </p>
      )}
      {!status && !busy && (
        <Button variant="secondary" onClick={() => void run('load')}>
          Retry FIRMS status
        </Button>
      )}
      {status && (
        <>
          <dl className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4 [&>div]:rounded-lg [&>div]:border [&>div]:border-line/70 [&>div]:bg-ground/40 [&>div]:p-3">
            <div>
              <dt className="text-xs text-muted">Current connection</dt>
              <dd className="mt-1 font-medium">
                {status.configured ? 'Key configured (hidden)' : 'No key configured'}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-muted">Managed through</dt>
              <dd className="mt-1">
                {status.credential_origin === 'environment'
                  ? 'Operator environment'
                  : status.credential_origin === 'database'
                    ? 'Encrypted application storage'
                    : 'Not configured'}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-muted">Collection area (operator setting)</dt>
              <dd className="mt-1 break-words font-mono text-xs">{status.area}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted">Connection use</dt>
              <dd className="mt-1 font-mono">
                {status.environment_disabled
                  ? 'Disabled by operator'
                  : status.configured
                    ? 'Ready for enabled source polls'
                    : 'Awaiting a tested connection'}
              </dd>
            </div>
          </dl>
          {status.environment_disabled && (
            <Alert tone="info">
              FIRMS is disabled by operator configuration. The operator must update the server
              configuration before connection changes or collection can resume.
            </Alert>
          )}
          {status.credential_origin === 'environment' && (
            <p className="text-sm text-muted">
              The environment MAP_KEY takes precedence. This connection is read-only here; the
              operator manages it on the server.
            </p>
          )}
          {!status.encryption_available && status.credential_origin !== 'environment' && (
            <Alert tone="info">
              Encrypted credential storage is unavailable. The operator must configure server-side
              encryption before an administrator can save a MAP_KEY.
            </Alert>
          )}
          <div className="flex flex-wrap gap-2">
            <Button variant="secondary" disabled={!!busy} onClick={() => void run('load')}>
              Refresh FIRMS status
            </Button>
            <Button
              variant="secondary"
              disabled={!!busy || !status.configured || status.environment_disabled}
              onClick={() => void run('current')}
            >
              Test current FIRMS connection
            </Button>
          </div>
          {editable && (
            <div className="grid gap-6 border-t border-line/70 pt-4 lg:grid-cols-2">
              <div className="space-y-3">
                <h3 className="text-sm font-semibold">1. Enter and test a replacement</h3>
                <TextField
                  label="NASA FIRMS MAP_KEY"
                  type="password"
                  autoComplete="new-password"
                  spellCheck={false}
                  maxLength={128}
                  value={connection.apiKey}
                  onChange={(event) => connection.changeKey(event.target.value)}
                  hint="Use 16 to 128 letters, numbers, underscores or hyphens. The key is never returned or shown again. It is cleared from this form when testing starts."
                />
                <Button
                  disabled={!!busy || (!connection.apiKey && !status.draft_present)}
                  onClick={() => void run('draft')}
                >
                  {connection.apiKey
                    ? 'Save draft and test'
                    : status.draft_present
                      ? 'Test saved FIRMS draft'
                      : 'Save draft and test'}
                </Button>
                {status.draft_present && (
                  <p className="text-xs text-muted">
                    A private draft exists.{' '}
                    {status.draft_expires_at
                      ? `Expires ${new Date(status.draft_expires_at).toLocaleString('en-GB')}.`
                      : 'Refresh to check its expiry.'}{' '}
                    It is not the active connection.
                  </p>
                )}
              </div>
              <div className="space-y-3">
                <h3 className="text-sm font-semibold">2. Review and confirm</h3>
                <p className="text-sm text-muted">
                  Confirmation replaces the stored connection globally. It takes effect on the next
                  scheduled poll and does not enable a disabled source.
                </p>
                {connection.proofExpired && (
                  <Alert tone="info">
                    The test or draft has expired. Run another test before confirming.
                  </Alert>
                )}
                {connection.canConfirm && (
                  <p className="text-xs">
                    Test completed
                    {status.tested_at
                      ? ` at ${new Date(status.tested_at).toLocaleString('en-GB')}`
                      : ''}
                    . Confirm within 15 minutes of the test and before the draft expires.
                  </p>
                )}
                <Button
                  disabled={!!busy || !connection.canConfirm}
                  onClick={() => void run('confirm')}
                >
                  Confirm FIRMS connection for everyone
                </Button>
              </div>
            </div>
          )}
          {editable && (status.configured || status.draft_present) && (
            <div className="space-y-2 rounded-lg border border-critical/30 bg-critical/5 p-3">
              {!connection.removeReview ? (
                <Button
                  variant="ghost"
                  disabled={!!busy}
                  onClick={() => connection.setRemoveReview(true)}
                >
                  Remove stored FIRMS connection
                </Button>
              ) : (
                <>
                  <p className="text-sm">
                    Remove the active stored MAP_KEY and its draft for everyone? Future polls will
                    have no stored key. Existing observations and reports remain available.
                  </p>
                  <div className="flex flex-wrap gap-2">
                    <Button variant="danger" disabled={!!busy} onClick={() => void run('remove')}>
                      Confirm removal of FIRMS connection
                    </Button>
                    <Button
                      variant="ghost"
                      disabled={!!busy}
                      onClick={() => connection.setRemoveReview(false)}
                    >
                      Keep connection
                    </Button>
                  </div>
                </>
              )}
            </div>
          )}
        </>
      )}
      {busy && (
        <div className="flex flex-wrap items-center gap-3">
          <LoadingNote
            label={
              busy === 'draft'
                ? 'Saving and testing the FIRMS draft'
                : busy === 'current'
                  ? 'Testing the current FIRMS connection'
                  : busy === 'confirm'
                    ? 'Confirming FIRMS connection'
                    : busy === 'remove'
                      ? 'Removing FIRMS connection'
                      : 'Checking FIRMS status'
            }
          />
          <Button variant="ghost" onClick={connection.cancel}>
            Cancel FIRMS request
          </Button>
        </div>
      )}
    </div>
  );
}

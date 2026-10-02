import { useCallback, useState } from 'react';
import { Link } from 'react-router';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SelectField, TextField } from '@/components/ui/Field';
import {
  getAlertDestinations,
  getAlertRoute,
  registerAlertDestination,
  removeAlertDestination,
  saveAlertRoute,
} from '@/lib/api/alertRouting';
import type { AlertDestination, AlertRoute } from '@/lib/api/alertRouting';
import { describeError, isApiError } from '@/lib/api/errors';
import type { Indicator } from '@/lib/api/warning';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { InstallationCopyNotice } from './InstallationCopyNotice';

function RoutingFields({
  indicator,
  initial,
  initialDestinations,
  onReload,
}: {
  indicator: Indicator;
  initial: AlertRoute;
  initialDestinations: AlertDestination[];
  onReload: () => Promise<void>;
}) {
  const [route, setRoute] = useState(initial);
  const [destinations, setDestinations] = useState(initialDestinations);
  const [name, setName] = useState('');
  const [url, setUrl] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [needsReload, setNeedsReload] = useState(false);
  async function action(run: () => Promise<void>) {
    setBusy(true);
    setError(null);
    setSaved(false);
    try {
      await run();
    } catch (reason) {
      setError(describeError(reason));
      if (isApiError(reason) && reason.status === 409) setNeedsReload(true);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section
      aria-label={`Notification routing for ${indicator.name}`}
      className="space-y-3 rounded border border-line bg-surface p-4"
    >
      <h3 className="font-medium">Notification destinations: {indicator.name}</h3>
      <InstallationCopyNotice />
      {error && <Alert tone="error">{error}</Alert>}
      {needsReload && (
        <div className="space-y-2">
          <p>Reloading replaces unsaved routing changes with the current saved settings.</p>
          <Button variant="secondary" disabled={busy} onClick={() => void onReload()}>
            Reload notification routing
          </Button>
        </div>
      )}
      {!route.can_manage && (
        <p>
          Only the personal rule owner, a team manager or an administrator can change external
          routing.
        </p>
      )}
      <fieldset disabled={busy || needsReload || !route.can_manage} className="space-y-3">
        <label className="flex gap-2 text-sm">
          <input type="checkbox" checked disabled />
          Store alerts in the application (always on)
        </label>
        <label className="flex gap-2 text-sm">
          <input
            type="checkbox"
            checked={route.email_enabled}
            onChange={(event) => {
              setSaved(false);
              setRoute({ ...route, email_enabled: event.target.checked });
            }}
          />
          Email me when this rule fires
        </label>
        <p className="text-xs text-muted">
          Email goes to the person who last saved this routing. Saving switches future mail to your
          own account address. Email also requires verification and your account opt-in in{' '}
          <Link className="underline" to="/account?section=notifications">
            Notification settings
          </Link>
          . Turning off account email cancels queued mail.
        </p>
        <SelectField
          label="Registered webhook destination"
          value={route.webhook_id ?? ''}
          onChange={(event) => {
            setSaved(false);
            setRoute({ ...route, webhook_id: event.target.value || null });
          }}
          options={[
            { value: '', label: 'No rule webhook' },
            ...destinations.map((item) => ({ value: item.id, label: item.name })),
          ]}
        />
        <p className="text-xs text-muted">
          The webhook receives the rule name, alert title and summary, countries and event IDs. Only
          destinations in this rule's workspace can be selected.
        </p>
        <Button
          onClick={() =>
            void action(async () => {
              setRoute(
                await saveAlertRoute(indicator.id, {
                  email_enabled: route.email_enabled,
                  webhook_id: route.webhook_id,
                  expected_revision: route.revision,
                }),
              );
              setSaved(true);
            })
          }
        >
          Save notification routing
        </Button>
        <details>
          <summary className="cursor-pointer text-sm">Register or remove a webhook</summary>
          <div className="mt-3 space-y-3">
            <TextField
              label="Destination name"
              value={name}
              maxLength={100}
              onChange={(event) => setName(event.target.value)}
            />
            <TextField
              label="HTTPS webhook URL"
              type="password"
              autoComplete="off"
              value={url}
              maxLength={2048}
              onChange={(event) => setUrl(event.target.value)}
              hint="Stored encrypted. The URL is not returned after registration."
            />
            <Button
              disabled={!name.trim() || !url.trim()}
              onClick={() =>
                void action(async () => {
                  const created = await registerAlertDestination({
                    name,
                    url,
                    team_id: indicator.team_id,
                  });
                  setDestinations([...destinations, created]);
                  setName('');
                  setUrl('');
                })
              }
            >
              Register webhook
            </Button>
            {destinations.map((item) => (
              <div key={item.id} className="flex items-center gap-3 text-sm">
                <span>{item.name}</span>
                <Button
                  variant="danger"
                  onClick={() =>
                    void action(async () => {
                      await removeAlertDestination(item.id);
                      setDestinations(destinations.filter((other) => other.id !== item.id));
                      if (route.webhook_id === item.id) setRoute({ ...route, webhook_id: null });
                    })
                  }
                >
                  Remove {item.name}
                </Button>
              </div>
            ))}
          </div>
        </details>
      </fieldset>
      {saved && <p role="status">Notification routing saved.</p>}
      <p className="text-xs text-muted">
        Unavailable destinations do not stop alerts. Ambiguous external sends are not automatically
        repeated.
      </p>
    </section>
  );
}

export function AlertRoutingPanel({ indicator }: { indicator: Indicator }) {
  const load = useCallback(async () => {
    const route = await getAlertRoute(indicator.id);
    const destinations = route.can_manage ? await getAlertDestinations(indicator.team_id) : [];
    return { route, destinations };
  }, [indicator.id, indicator.team_id]);
  const result = useScopedResource(load);
  if (result.error)
    return (
      <div className="space-y-2">
        <Alert tone="error">{describeError(result.error)}</Alert>
        <Button variant="secondary" onClick={() => void result.reload()}>
          Retry loading notification routing
        </Button>
      </div>
    );
  if (!result.data) return <LoadingNote label="Loading notification routing" />;
  return (
    <RoutingFields
      key={`${indicator.id}:${result.data.route.revision}`}
      indicator={indicator}
      initial={result.data.route}
      initialDestinations={result.data.destinations}
      onReload={result.reload}
    />
  );
}

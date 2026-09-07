import { useCallback } from 'react';
import { Link } from 'react-router';

import { Alert as Notice, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { Table, Td, Th } from '@/components/ui/Table';
import { describeError } from '@/lib/api/errors';
import { fetchTemplates } from '@/lib/api/reports';
import {
  acknowledgeAlert,
  createIndicator,
  deleteIndicator,
  fetchAlerts,
  fetchIndicators,
} from '@/lib/api/warning';
import type { Alert, Indicator, IndicatorRequest } from '@/lib/api/warning';
import { formatAgo } from '@/lib/format';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';
import { useNow } from '@/lib/hooks/useNow';
import { useResource } from '@/lib/hooks/useResource';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { useWorkspaces } from '@/lib/hooks/useWorkspaces';
import { fetchPlans } from '@/lib/api/direction';

import { AlertDestination } from './AlertDestination';
import { IndicatorForm, describeWindow } from './IndicatorForm';

function describeScope(indicator: Indicator): string {
  if (indicator.bbox !== null) return `box ${indicator.bbox.map((n) => n.toFixed(1)).join(', ')}`;
  if (indicator.countries.length > 0) return indicator.countries.join(', ');
  return 'anywhere';
}

function describeRule(indicator: Indicator): string {
  const what = [
    indicator.categories.length > 0 ? indicator.categories.join('/') : 'any category',
    indicator.keywords.length > 0 ? `with ${indicator.keywords.join(', ')}` : '',
  ]
    .filter((part) => part !== '')
    .join(' ');
  return `${String(indicator.threshold)} or more ${what} in ${describeWindow(indicator.window_minutes)}`;
}

function AlertItem({
  alert,
  onAcknowledge,
  workspace,
  canAcknowledge,
}: {
  alert: Alert;
  onAcknowledge: () => void;
  workspace: string;
  canAcknowledge: boolean;
}) {
  const now = useNow();
  return (
    <li className="flex flex-col gap-1 rounded-card border border-line bg-surface p-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <span className="font-medium">
          {alert.title}
          <span className="ml-2 text-xs text-muted">{workspace}</span>
        </span>
        <span className="font-mono text-xs text-muted">{formatAgo(alert.fired_at, now)}</span>
      </div>
      {alert.summary !== '' && <p className="text-xs text-muted">{alert.summary}</p>}
      <div className="flex flex-wrap items-center gap-3 text-xs">
        {alert.countries.length > 0 && (
          <span className="font-mono text-muted">{alert.countries.join(', ')}</span>
        )}
        <AlertDestination
          monitorId={alert.annotation_monitor_id}
          transitionId={alert.annotation_transition_id}
          reportId={alert.report_id}
        />
        {alert.acknowledged_at === null ? (
          <Button variant="secondary" disabled={!canAcknowledge} onClick={onAcknowledge}>
            Acknowledge
          </Button>
        ) : (
          <span className="text-muted">acknowledged</span>
        )}
      </div>
    </li>
  );
}

export default function WarningPage() {
  const workspaces = useWorkspaces();
  const plans = useScopedResource(fetchPlans);
  const alerts = useScopedResource(fetchAlerts);
  const indicators = useScopedResource(fetchIndicators);
  const templates = useResource(fetchTemplates);
  const reloadIndicators = indicators.reload;
  const setAlerts = alerts.setData;

  const create = useAsyncAction(
    useCallback(
      async (request: IndicatorRequest) => {
        await createIndicator(request);
        await reloadIndicators();
      },
      [reloadIndicators],
    ),
  );
  const remove = useAsyncAction(
    useCallback(
      async (id: string) => {
        await deleteIndicator(id);
        await reloadIndicators();
      },
      [reloadIndicators],
    ),
  );
  const acknowledge = useAsyncAction(
    useCallback(
      async (id: string) => {
        const updated = await acknowledgeAlert(id);
        setAlerts((page) =>
          page === null
            ? page
            : {
                items: page.items.map((item) => (item.id === updated.id ? updated : item)),
                unacknowledged: Math.max(0, page.unacknowledged - 1),
              },
        );
      },
      [setAlerts],
    ),
  );

  return (
    <section className="flex h-full flex-col gap-6 overflow-y-auto p-6">
      <h1 className="text-xl font-semibold">Warning</h1>
      <Link to="/annotation-monitors" className="text-sm text-ember underline">
        Annotation monitors and exact transition history
      </Link>
      <p className="text-sm text-muted">
        Indicators are standing rules over the live picture. When one fires, the alert lands here
        and on the stream, goes to the webhook when one is configured, and can open a report.
      </p>
      <div className="flex flex-col gap-3">
        <h2 className="text-base font-semibold">Alerts</h2>
        {alerts.error === null ? null : <Notice tone="error">{describeError(alerts.error)}</Notice>}
        {acknowledge.error === null ? null : (
          <Notice tone="error">{describeError(acknowledge.error)}</Notice>
        )}
        {alerts.data === null ? (
          alerts.loading ? (
            <LoadingNote label="Loading alerts" />
          ) : null
        ) : alerts.data.items.length === 0 ? (
          <p className="text-sm text-muted">Nothing has fired in the last week.</p>
        ) : (
          <ul aria-label="Alerts" className="flex flex-col gap-2">
            {alerts.data.items.map((item) => (
              <AlertItem
                key={item.id}
                alert={item}
                workspace={workspaces.label(item.team_id)}
                canAcknowledge={workspaces.canAcknowledge(item.team_id)}
                onAcknowledge={() => void acknowledge.run(item.id)}
              />
            ))}
          </ul>
        )}
      </div>
      <div className="flex flex-col gap-3">
        <h2 className="text-base font-semibold">Indicators</h2>
        {indicators.error === null ? null : (
          <Notice tone="error">{describeError(indicators.error)}</Notice>
        )}
        {remove.error === null ? null : <Notice tone="error">{describeError(remove.error)}</Notice>}
        {indicators.data === null ? (
          indicators.loading ? (
            <LoadingNote label="Loading indicators" />
          ) : null
        ) : indicators.data.length === 0 ? (
          <p className="text-sm text-muted">No indicators yet.</p>
        ) : (
          <Table caption="Indicators">
            <thead>
              <tr>
                <Th>Indicator</Th>
                <Th>Scope</Th>
                <Th>Rule</Th>
                <Th>Report</Th>
                <Th />
              </tr>
            </thead>
            <tbody>
              {indicators.data.map((item) => (
                <tr key={item.id} className={item.enabled ? '' : 'opacity-60'}>
                  <Td className="font-medium">
                    {item.name}
                    <div className="text-xs text-muted">{workspaces.label(item.team_id)}</div>
                  </Td>
                  <Td className="font-mono text-xs text-muted">{describeScope(item)}</Td>
                  <Td className="text-xs">{describeRule(item)}</Td>
                  <Td className="font-mono text-xs text-muted">{item.report_template ?? 'none'}</Td>
                  <Td>
                    <Button
                      disabled={!workspaces.canManage(item)}
                      variant="danger"
                      busy={remove.busy}
                      onClick={() => void remove.run(item.id)}
                    >
                      Delete
                    </Button>
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
        <IndicatorForm
          key={workspaces.key}
          workspaces={workspaces}
          plans={plans.data ?? []}
          templates={templates.data ?? []}
          busy={create.busy}
          error={create.error === null ? null : describeError(create.error)}
          onSubmit={(request) => void create.run(request)}
        />
      </div>
    </section>
  );
}

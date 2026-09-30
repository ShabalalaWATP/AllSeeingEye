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
import type { AlertAcknowledgementRequest, Indicator, IndicatorRequest } from '@/lib/api/warning';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';
import { useResource } from '@/lib/hooks/useResource';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { useWorkspaces } from '@/lib/hooks/useWorkspaces';
import { fetchPlans } from '@/lib/api/direction';
import { clearAreaWatchDraft, useAreaWatchDraft } from '@/lib/areaWatchDraft';

import { AlertItem } from './AlertItem';
import { RuleBaseline } from './RuleBaseline';
import { RuleFeedback } from './RuleFeedback';
import { IndicatorForm, describeWindow } from './IndicatorForm';

function describeScope(indicator: Indicator): string {
  if (indicator.research_area)
    return `exact shape · ${indicator.research_area.sha256.slice(0, 12)}`;
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
  if (indicator.baseline_ratio)
    return `${indicator.baseline_ratio} times the ${indicator.baseline_days ?? 30}-day hourly mean, at least ${indicator.threshold} items`;
  return `${String(indicator.threshold)} or more ${what} in ${describeWindow(indicator.window_minutes)}`;
}

export default function WarningPage() {
  const draft = useAreaWatchDraft();
  const draftId = draft?.id;
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
        if (draftId !== undefined) clearAreaWatchDraft(draftId);
        await reloadIndicators();
      },
      [reloadIndicators, draftId],
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
      async (id: string, feedback: AlertAcknowledgementRequest) => {
        const updated = await acknowledgeAlert(id, feedback);
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

  const form = (
    <IndicatorForm
      key={`${workspaces.key}:${draftId ?? ''}`}
      draft={draft}
      workspaces={workspaces}
      plans={plans.data ?? []}
      templates={templates.data ?? []}
      busy={create.busy}
      error={create.error === null ? null : describeError(create.error)}
      onSubmit={(request) => void create.run(request)}
    />
  );

  return (
    <section className="flex h-full flex-col gap-6 overflow-y-auto p-6">
      <h1 className="text-xl font-semibold">Alerts</h1>
      <Link to="/annotation-monitors" className="text-sm text-ember underline">
        Annotation monitors and their change history
      </Link>
      <p className="text-sm text-muted">
        Review changes that need attention and set rules for activity in connected feeds. For a
        question answered every week or month, set up a{' '}
        <Link to="/subscriptions" className="text-text underline">
          subscription
        </Link>
        .
      </p>
      {draft && form}
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
                onAcknowledge={(feedback) => void acknowledge.run(item.id, feedback)}
              />
            ))}
          </ul>
        )}
      </div>
      <div className="flex flex-col gap-3">
        <h2 className="text-base font-semibold">Alert rules</h2>
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
                  <Td className="text-xs">
                    {describeRule(item)}
                    <RuleFeedback ruleId={item.id} />
                    {item.baseline_ratio && <RuleBaseline ruleId={item.id} />}
                  </Td>
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
        {!draft && form}
      </div>
    </section>
  );
}

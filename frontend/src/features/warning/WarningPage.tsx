import { useCallback, useRef } from 'react';
import { Link } from 'react-router';

import { Alert as Notice, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { Table, Td, Th } from '@/components/ui/Table';
import { describeError } from '@/lib/api/errors';
import { fetchTemplates } from '@/lib/api/reports';
import { createIndicator, deleteIndicator, fetchIndicators } from '@/lib/api/warning';
import type { Indicator, IndicatorRequest } from '@/lib/api/warning';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';
import { useConfirmedAction } from '@/lib/hooks/useConfirmedAction';
import { useResource } from '@/lib/hooks/useResource';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { useWorkspaces } from '@/lib/hooks/useWorkspaces';
import { fetchPlans } from '@/lib/api/direction';
import { clearAreaWatchDraft, useAreaWatchDraft } from '@/lib/areaWatchDraft';
import { clearDraft, draftForms } from '@/lib/formDrafts';

import { AlertsSection } from './AlertsSection';
import { IndicatorForm, describeWindow } from './IndicatorForm';
import { RuleDeletion } from './RuleDeletion';

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
  return `${String(indicator.threshold)} or more ${what} in ${describeWindow(indicator.window_minutes)}`;
}

export default function WarningPage() {
  const draft = useAreaWatchDraft();
  const draftId = draft?.id;
  const workspaces = useWorkspaces();
  const plans = useScopedResource(fetchPlans);
  const indicators = useScopedResource(fetchIndicators);
  const templates = useResource(fetchTemplates);
  const reloadIndicators = indicators.reload;

  const create = useAsyncAction(
    useCallback(
      async (request: IndicatorRequest) => {
        await createIndicator(request);
        clearDraft(draftForms.alertRule(draftId));
        if (draftId !== undefined) clearAreaWatchDraft(draftId);
        await reloadIndicators();
      },
      [reloadIndicators, draftId],
    ),
  );
  const rulesHeading = useRef<HTMLHeadingElement>(null);
  const remove = useConfirmedAction(
    useCallback(
      async (rule: Indicator) => {
        await deleteIndicator(rule.id);
        await reloadIndicators();
      },
      [reloadIndicators],
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
      error={create.error}
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
      <AlertsSection workspaces={workspaces} />
      <div className="flex flex-col gap-3">
        <h2 ref={rulesHeading} className="text-base font-semibold">
          Alert rules
        </h2>
        {indicators.error === null ? null : (
          <Notice tone="error">{describeError(indicators.error)}</Notice>
        )}
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
                      aria-haspopup="dialog"
                      onClick={() => remove.ask(item)}
                    >
                      Delete
                    </Button>
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
        <RuleDeletion
          action={remove}
          workspaceLabel={workspaces.label}
          describe={describeRule}
          returnFocus={rulesHeading}
        />
        {!draft && form}
      </div>
    </section>
  );
}

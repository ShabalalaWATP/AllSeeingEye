import { useCallback, useRef, useState } from 'react';
import { Link } from 'react-router';

import { Alert as Notice } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import type { IndicatorRequest } from '@/lib/alertRules';
import { clearReportWatchDraft, useReportWatchDraft } from '@/lib/alertRuleDraft';
import type { ReportWatchSource } from '@/lib/alertRuleDraft';
import { fetchPlans } from '@/lib/api/direction';
import { fetchCountries } from '@/lib/api/geo';
import { fetchTemplates } from '@/lib/api/reports';
import {
  createIndicator,
  deleteIndicator,
  fetchIndicators,
  updateIndicator,
} from '@/lib/api/warning';
import type { Indicator } from '@/lib/api/warning';
import { clearAreaWatchDraft, useAreaWatchDraft } from '@/lib/areaWatchDraft';
import { clearDraft, draftForms } from '@/lib/formDrafts';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';
import { useConfirmedAction } from '@/lib/hooks/useConfirmedAction';
import { useResource } from '@/lib/hooks/useResource';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { useWorkspaces } from '@/lib/hooks/useWorkspaces';

import { AlertsSection } from './AlertsSection';
import { AlertRulesSection } from './AlertRulesSection';
import { IndicatorForm } from './IndicatorForm';
import { reportVersionPath } from './RuleDraftNotice';
import { ruleUpdate } from './ruleUpdates';

interface Saved {
  message: string;
  source?: ReportWatchSource | undefined;
}

export default function WarningPage() {
  const reportDraft = useReportWatchDraft();
  const areaDraft = useAreaWatchDraft();
  const draft = reportDraft ?? areaDraft;
  const workspaces = useWorkspaces();
  const plans = useScopedResource(fetchPlans);
  const indicators = useScopedResource(fetchIndicators);
  const templates = useResource(fetchTemplates);
  const countries = useResource(fetchCountries);
  const reloadIndicators = indicators.reload;
  // The rule being edited is read from the latest list, so a reload re-opens its newest revision.
  const [editingId, setEditingId] = useState<string | null>(null);
  const editing = editingId
    ? (indicators.data?.find((rule) => rule.id === editingId) ?? null)
    : null;
  const [saved, setSaved] = useState<Saved | null>(null);
  const [toggling, setToggling] = useState<string | null>(null);
  const rulesHeading = useRef<HTMLHeadingElement>(null);

  const discardDraft = useCallback(() => {
    if (reportDraft) clearReportWatchDraft(reportDraft.id);
    else if (areaDraft) clearAreaWatchDraft(areaDraft.id);
  }, [reportDraft, areaDraft]);

  const create = useAsyncAction(
    useCallback(
      async (request: IndicatorRequest) => {
        const rule = await createIndicator(request);
        // Only a confirmed save clears the draft and reports success.
        clearDraft(
          draftForms.alertRule(reportDraft ? `report-${String(reportDraft.id)}` : areaDraft?.id),
        );
        discardDraft();
        setSaved({ message: `Alert rule “${rule.name}” added.`, source: reportDraft?.source });
        await reloadIndicators();
      },
      [reloadIndicators, reportDraft, areaDraft, discardDraft],
    ),
  );
  const edit = useAsyncAction(
    useCallback(
      async (rule: Indicator, request: IndicatorRequest, confirmWider: boolean) => {
        const updated = await updateIndicator(rule.id, ruleUpdate(rule, request, confirmWider));
        setEditingId(null);
        setSaved({ message: `Changes to “${updated.name}” saved.` });
        await reloadIndicators();
      },
      [reloadIndicators],
    ),
  );
  const toggle = useAsyncAction(
    useCallback(
      async (rule: Indicator) => {
        setToggling(rule.id);
        try {
          const updated = await updateIndicator(rule.id, ruleUpdate(rule, null, false));
          setSaved({
            message: updated.enabled
              ? `“${updated.name}” resumed. It counts only activity from now on.`
              : `“${updated.name}” paused. It is not evaluated and raises no alerts until resumed.`,
          });
          await reloadIndicators();
        } finally {
          setToggling(null);
        }
      },
      [reloadIndicators],
    ),
  );
  const remove = useConfirmedAction(
    useCallback(
      async (rule: Indicator) => {
        await deleteIndicator(rule.id);
        await reloadIndicators();
      },
      [reloadIndicators],
    ),
  );
  const shared = {
    workspaces,
    plans: plans.data ?? [],
    templates: templates.data ?? [],
    countries: countries.data,
  };
  const form = editing ? (
    <IndicatorForm
      key={`edit:${editing.id}:${editing.updated_at}`}
      {...shared}
      mode={{ kind: 'edit', rule: editing }}
      busy={edit.busy}
      error={edit.error}
      onSubmit={(request, { confirmWider }) => void edit.run(editing, request, confirmWider)}
      onDiscardDraft={discardDraft}
      onCancel={() => {
        edit.clearError();
        setEditingId(null);
      }}
    />
  ) : (
    <IndicatorForm
      key={`${workspaces.key}:${reportDraft ? `report-${String(reportDraft.id)}` : String(areaDraft?.id ?? '')}`}
      {...shared}
      mode={{ kind: 'create', areaDraft: reportDraft ? null : areaDraft, reportDraft }}
      busy={create.busy}
      error={create.error}
      onSubmit={(request) => void create.run(request)}
      onDiscardDraft={discardDraft}
    />
  );
  const stale = edit.error?.status === 409 || toggle.error?.status === 409;

  return (
    <section className="flex h-full flex-col gap-6 overflow-y-auto p-6">
      <h1 className="text-xl font-semibold">Alerts</h1>
      <Link to="/annotation-monitors" className="text-sm text-ember underline">
        Annotation monitors and their change history
      </Link>
      <p className="text-sm text-muted">
        Review changes that need attention and set alert rules for activity in connected feeds. For
        a question answered every week or month, set up a{' '}
        <Link to="/subscriptions" className="text-text underline">
          subscription
        </Link>
        .
      </p>
      {saved && (
        <Notice tone="success">
          {saved.message}{' '}
          {saved.source && (
            <Link to={reportVersionPath(saved.source)} className="underline">
              Back to “{saved.source.title}”, version {saved.source.version}
            </Link>
          )}
        </Notice>
      )}
      {draft && !editing && form}
      <AlertsSection workspaces={workspaces} />
      <AlertRulesSection
        rules={indicators.data}
        loading={indicators.loading}
        error={indicators.error ?? toggle.error}
        workspaces={workspaces}
        heading={rulesHeading}
        remove={remove}
        toggling={toggling}
        onEdit={(rule) => {
          setSaved(null);
          edit.clearError();
          setEditingId(rule.id);
        }}
        onToggle={(rule) => {
          setSaved(null);
          void toggle.run(rule);
        }}
      >
        {stale && (
          <Button
            variant="secondary"
            onClick={() => {
              edit.clearError();
              toggle.clearError();
              void reloadIndicators();
            }}
          >
            Reload the latest alert rules
          </Button>
        )}
        {(editing !== null || !draft) && form}
      </AlertRulesSection>
    </section>
  );
}

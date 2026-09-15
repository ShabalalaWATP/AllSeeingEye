import { useCallback, useEffect, useRef, useState } from 'react';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { Table, Th } from '@/components/ui/Table';
import { describeError } from '@/lib/api/errors';
import type { Country } from '@/lib/api/geoSchemas';
import type { ReportTemplate } from '@/lib/api/reports';
import {
  createSchedule,
  deleteSchedule,
  fetchSchedules,
  pauseSchedule,
  resumeSchedule,
  updateSchedule,
} from '@/lib/api/schedules';
import type { Schedule, ScheduleRequest } from '@/lib/api/schedules';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import type { CollectionPlan } from '@/lib/api/direction';
import type { Workspaces } from '@/lib/hooks/useWorkspaces';

import { ScheduleForm } from './ScheduleForm';
import { ScheduleRow } from './ScheduleRow';
import { scheduleListSummary } from './scheduleListSummary';
import { SelectField, TextField } from '@/components/ui/Field';
import { useScheduleRefresh } from './useScheduleRefresh';
import { SubscriptionUsage } from './SubscriptionUsage';
import { runSubscriptionNow } from '@/lib/api/subscriptionControls';

/** Standing orders for products, produced by the server as their owner at the chosen hour. */
export function SchedulesSection({
  templates,
  workspaces,
  plans,
  countries,
  draftQuestion = '',
  draftCountry = '',
}: {
  templates: readonly ReportTemplate[];
  plans: readonly CollectionPlan[];
  workspaces: Workspaces;
  countries: readonly Country[];
  draftQuestion?: string;
  draftCountry?: string;
}) {
  const [editing, setEditing] = useState<Schedule | null>(null);
  const [copying, setCopying] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);
  const [status, setStatus] = useState('all');
  const [cadenceFilter, setCadenceFilter] = useState('all');
  const [search, setSearch] = useState('');
  const editTrigger = useRef<HTMLButtonElement>(null);
  const formContainer = useRef<HTMLDivElement>(null);
  const listHeading = useRef<HTMLHeadingElement>(null);
  const runRequestIds = useRef(new Map<string, string>());
  const schedules = useScopedResource(fetchSchedules);
  const refreshError = useScheduleRefresh(schedules.data, schedules.key, schedules.setData);
  const reload = schedules.reload;
  useEffect(() => {
    if (!editing) return;
    const container = formContainer.current;
    const scroll: unknown = container && Reflect.get(container, 'scrollIntoView');
    if (typeof scroll === 'function') scroll.call(container, { block: 'start' });
    formContainer.current?.querySelector<HTMLElement>('h2')?.focus();
  }, [editing]);
  const restoreEditFocus = useCallback(() => {
    const target = editTrigger.current;
    if (target?.isConnected) target.focus();
    else listHeading.current?.focus();
    editTrigger.current = null;
  }, []);
  const save = useAsyncAction(
    useCallback(
      async (request: ScheduleRequest) => {
        if (editing && !copying) await updateSchedule(editing.id, request);
        else await createSchedule(request);
        setNotice(
          editing && !copying
            ? 'Subscription updated.'
            : copying
              ? 'Paused copy created. Resume it when you are ready for new runs.'
              : 'Subscription created. Your first update will appear after the next scheduled run.',
        );
        restoreEditFocus();
        setEditing(null);
        setCopying(false);
        setRevision((value) => value + 1);
        await reload();
      },
      [reload, editing, copying, restoreEditFocus],
    ),
  );
  const remove = useAsyncAction(
    useCallback(
      async (id: string) => {
        await deleteSchedule(id);
        setEditing((current) => (current?.id === id ? null : current));
        await reload();
      },
      [reload],
    ),
  );
  const toggle = useAsyncAction(
    useCallback(
      async (schedule: Schedule) => {
        const updated = schedule.enabled
          ? await pauseSchedule(schedule.id)
          : await resumeSchedule(schedule.id);
        setEditing((current) => (current?.id === updated.id ? updated : current));
        await reload();
      },
      [reload],
    ),
  );
  const runNow = useAsyncAction(
    useCallback(
      async (id: string) => {
        const requestId = runRequestIds.current.get(id) ?? crypto.randomUUID();
        runRequestIds.current.set(id, requestId);
        await runSubscriptionNow(id, requestId);
        runRequestIds.current.delete(id);
        setNotice('A new report has been queued. Follow its progress in edition history.');
        await reload();
      },
      [reload],
    ),
  );
  const {
    visible: visibleSchedules,
    active,
    paused,
    figures,
  } = scheduleListSummary(schedules.data ?? [], status, cadenceFilter, search);
  return (
    <div className="flex flex-col gap-5">
      {schedules.data && (
        <ul aria-label="Subscription figures" className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {figures.map((figure) => (
            <li
              key={figure.label}
              className="rounded-xl border border-line/70 bg-surface/60 px-4 py-3"
            >
              <p className="text-[11px] text-muted">{figure.label}</p>
              <p className={`mt-1 truncate text-xl font-semibold tracking-tight ${figure.tone}`}>
                {figure.value}
              </p>
            </li>
          ))}
        </ul>
      )}
      {schedules.data && <SubscriptionUsage subscriptions={schedules.data} />}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 ref={listHeading} tabIndex={-1} className="text-base font-semibold">
            Your subscriptions
          </h2>
          <p className="mt-1 text-xs text-muted">
            {active.length} active · {paused.length} paused
          </p>
        </div>
        <div className="grid w-full gap-3 sm:grid-cols-3 lg:w-auto">
          <TextField
            label="Search subscriptions"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Topic or question"
          />
          <SelectField
            label="Show subscriptions"
            value={status}
            onChange={(event) => setStatus(event.target.value)}
            options={[
              { value: 'all', label: 'All subscriptions' },
              { value: 'active', label: 'Active' },
              { value: 'paused', label: 'Paused' },
              { value: 'attention', label: 'Needs attention' },
            ]}
          />
          <SelectField
            label="Update frequency"
            value={cadenceFilter}
            onChange={(event) => setCadenceFilter(event.target.value)}
            options={[
              { value: 'all', label: 'Any frequency' },
              { value: 'daily', label: 'Daily' },
              { value: 'weekdays', label: 'Weekdays' },
              { value: 'weekly', label: 'Weekly' },
              { value: 'monthly', label: 'Monthly' },
              { value: 'quarterly', label: 'Every 3 months' },
              { value: 'semiannual', label: 'Every 6 months' },
              { value: 'annual', label: 'Annual' },
            ]}
          />
        </div>
      </div>
      <p className="text-sm text-muted">
        Review the latest update, compare the previous report, or pause future runs.
      </p>
      {schedules.error && (
        <Alert tone="error">
          {describeError(schedules.error)}{' '}
          <Button variant="secondary" onClick={() => void reload()}>
            Retry subscriptions
          </Button>
        </Alert>
      )}
      {refreshError && !schedules.error && (
        <Alert tone={schedules.data ? 'warning' : 'error'}>
          Subscription status could not be refreshed.{' '}
          {schedules.data ? 'Showing the last loaded results. ' : 'The old list has been hidden. '}
          {refreshError}{' '}
          <Button variant="secondary" onClick={() => void reload()}>
            Retry subscriptions
          </Button>
        </Alert>
      )}
      {notice && (
        <p role="status" className="py-2 text-sm text-ember">
          {notice}
        </p>
      )}
      {remove.error === null ? null : <Alert tone="error">{describeError(remove.error)}</Alert>}
      {toggle.error === null ? null : <Alert tone="error">{describeError(toggle.error)}</Alert>}
      {runNow.error === null ? null : <Alert tone="error">{describeError(runNow.error)}</Alert>}
      {schedules.data === null ? (
        schedules.loading ? (
          <LoadingNote label="Loading subscriptions" />
        ) : null
      ) : schedules.data.length === 0 ? (
        <p className="text-sm text-muted">
          No subscriptions yet. Choose a topic and create your first update below.
        </p>
      ) : (
        <Table caption="Subscriptions">
          <thead>
            <tr>
              <Th>Subscription</Th>
              <Th>Product</Th>
              <Th>When</Th>
              <Th>Next run</Th>
              <Th>Latest update</Th>
              <Th>Controls</Th>
            </tr>
          </thead>
          <tbody>
            {visibleSchedules.map((item) => (
              <ScheduleRow
                key={item.id}
                item={item}
                workspaces={workspaces}
                productTitle={
                  templates.find((template) => template.id === item.template_id)?.title ??
                  'Research report'
                }
                busy={toggle.busy || remove.busy || save.busy || runNow.busy}
                onToggle={(item) => void toggle.run(item)}
                onRunNow={(id) => void runNow.run(id)}
                onRemove={(id) => void remove.run(id)}
                onEdit={(item, trigger) => {
                  editTrigger.current = trigger;
                  setEditing(item);
                  setCopying(false);
                  save.clearError();
                  setNotice(null);
                }}
                onDuplicate={(item, trigger) => {
                  editTrigger.current = trigger;
                  setEditing({
                    ...item,
                    name: `Copy of ${item.name}`.slice(0, 120),
                    enabled: false,
                  });
                  setCopying(true);
                  save.clearError();
                  setNotice(null);
                }}
                onBriefCopied={() => {
                  setNotice(
                    'Paused copy created from the exact Research Brief revision. Resume it when ready.',
                  );
                  void reload();
                }}
              />
            ))}
            {visibleSchedules.length === 0 && (
              <tr>
                <td colSpan={6} className="p-5 text-sm text-muted">
                  No subscriptions match these filters.
                </td>
              </tr>
            )}
          </tbody>
        </Table>
      )}
      <div
        ref={formContainer}
        className="rounded-2xl border border-line/70 bg-surface/40 px-5 pb-6 sm:px-7"
      >
        <ScheduleForm
          key={`${workspaces.key}:${editing?.id ?? 'new'}:${copying}:${revision}`}
          initial={editing ?? undefined}
          duplicate={copying}
          draftQuestion={editing ? '' : draftQuestion}
          draftCountry={editing ? '' : draftCountry}
          onCancel={
            editing
              ? () => {
                  restoreEditFocus();
                  setEditing(null);
                  setCopying(false);
                  save.clearError();
                }
              : undefined
          }
          workspaces={workspaces}
          plans={plans}
          templates={templates}
          countries={countries}
          busy={save.busy || toggle.busy || remove.busy || runNow.busy}
          error={save.error === null ? null : describeError(save.error)}
          onSubmit={(request) => void save.run(request)}
        />
      </div>
    </div>
  );
}

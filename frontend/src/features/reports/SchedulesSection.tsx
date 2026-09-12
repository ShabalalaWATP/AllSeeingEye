import { useCallback, useState } from 'react';

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
  scheduleRequest,
  updateSchedule,
} from '@/lib/api/schedules';
import type { Schedule, ScheduleRequest } from '@/lib/api/schedules';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import type { CollectionPlan } from '@/lib/api/direction';
import type { Workspaces } from '@/lib/hooks/useWorkspaces';

import { ScheduleForm } from './ScheduleForm';
import { ScheduleRow } from './ScheduleRow';
import { SelectField } from '@/components/ui/Field';

/** Standing orders for products, produced by the server as their owner at the chosen hour. */
export function SchedulesSection({
  templates,
  workspaces,
  plans,
  countries,
}: {
  templates: readonly ReportTemplate[];
  plans: readonly CollectionPlan[];
  workspaces: Workspaces;
  countries: readonly Country[];
}) {
  const [editing, setEditing] = useState<Schedule | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);
  const [status, setStatus] = useState('all');
  const schedules = useScopedResource(fetchSchedules);
  const reload = schedules.reload;
  const save = useAsyncAction(
    useCallback(
      async (request: ScheduleRequest) => {
        if (editing) await updateSchedule(editing.id, request);
        else await createSchedule(request);
        setNotice(
          editing
            ? 'Schedule updated.'
            : 'Schedule created. Your first report will appear after the next scheduled run.',
        );
        setEditing(null);
        setRevision((value) => value + 1);
        await reload();
      },
      [reload, editing],
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
        const updated = await updateSchedule(
          schedule.id,
          scheduleRequest(schedule, !schedule.enabled),
        );
        setEditing((current) => (current?.id === updated.id ? updated : current));
        await reload();
      },
      [reload],
    ),
  );
  const visibleSchedules =
    schedules.data?.filter(
      (item) =>
        status === 'all' ||
        (status === 'active' && item.enabled) ||
        (status === 'paused' && !item.enabled) ||
        (status === 'attention' && item.last_error !== null),
    ) ?? [];
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold">Schedule control panel</h2>
          <p className="mt-1 text-xs text-muted">
            {schedules.data?.filter((item) => item.enabled).length ?? 0} active ·{' '}
            {schedules.data?.filter((item) => !item.enabled).length ?? 0} paused
          </p>
        </div>
        <SelectField
          label="Show schedules"
          value={status}
          onChange={(event) => setStatus(event.target.value)}
          options={[
            { value: 'all', label: 'All schedules' },
            { value: 'active', label: 'Active' },
            { value: 'paused', label: 'Paused' },
            { value: 'attention', label: 'Needs attention' },
          ]}
        />
      </div>
      <p className="text-sm text-muted">
        A saved report from every run. Pause a schedule to stop future research while keeping its
        history.
      </p>
      {schedules.error && (
        <Alert tone="error">
          {describeError(schedules.error)}{' '}
          <Button variant="secondary" onClick={() => void reload()}>
            Retry schedules
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
      {schedules.data === null ? (
        schedules.loading ? (
          <LoadingNote label="Loading schedules" />
        ) : null
      ) : schedules.data.length === 0 ? (
        <p className="text-sm text-muted">
          No schedules yet. Create your first recurring report below.
        </p>
      ) : (
        <Table caption="Schedules">
          <thead>
            <tr>
              <Th>Schedule</Th>
              <Th>Product</Th>
              <Th>When</Th>
              <Th>Next run</Th>
              <Th>Last run</Th>
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
                busy={toggle.busy || remove.busy || save.busy}
                onToggle={(item) => void toggle.run(item)}
                onRemove={(id) => void remove.run(id)}
                onEdit={(item) => {
                  setEditing(item);
                  save.clearError();
                  setNotice(null);
                }}
              />
            ))}
            {visibleSchedules.length === 0 && (
              <tr>
                <td colSpan={6} className="p-5 text-sm text-muted">
                  No schedules match this status.
                </td>
              </tr>
            )}
          </tbody>
        </Table>
      )}
      <ScheduleForm
        key={`${workspaces.key}:${editing?.id ?? 'new'}:${revision}`}
        initial={editing ?? undefined}
        onCancel={
          editing
            ? () => {
                setEditing(null);
                save.clearError();
              }
            : undefined
        }
        workspaces={workspaces}
        plans={plans}
        templates={templates}
        countries={countries}
        busy={save.busy || toggle.busy || remove.busy}
        error={save.error === null ? null : describeError(save.error)}
        onSubmit={(request) => void save.run(request)}
      />
    </div>
  );
}

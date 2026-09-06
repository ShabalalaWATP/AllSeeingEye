import { useCallback } from 'react';
import { Link } from 'react-router';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { Table, Td, Th } from '@/components/ui/Table';
import { describeError } from '@/lib/api/errors';
import type { Country } from '@/lib/api/geoSchemas';
import type { ReportTemplate } from '@/lib/api/reports';
import { createSchedule, deleteSchedule, fetchSchedules } from '@/lib/api/schedules';
import type { ScheduleRequest } from '@/lib/api/schedules';
import { formatUtc } from '@/lib/format';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import type { CollectionPlan } from '@/lib/api/direction';
import type { Workspaces } from '@/lib/hooks/useWorkspaces';

import { ScheduleForm, describeCadence } from './ScheduleForm';

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
  const schedules = useScopedResource(fetchSchedules);
  const reload = schedules.reload;
  const create = useAsyncAction(
    useCallback(
      async (request: ScheduleRequest) => {
        await createSchedule(request);
        await reload();
      },
      [reload],
    ),
  );
  const remove = useAsyncAction(
    useCallback(
      async (id: string) => {
        await deleteSchedule(id);
        await reload();
      },
      [reload],
    ),
  );
  return (
    <div className="flex flex-col gap-3">
      <h2 className="text-base font-semibold">Schedules</h2>
      {schedules.error === null ? null : (
        <Alert tone="error">{describeError(schedules.error)}</Alert>
      )}
      {remove.error === null ? null : <Alert tone="error">{describeError(remove.error)}</Alert>}
      {schedules.data === null ? (
        schedules.loading ? (
          <LoadingNote label="Loading schedules" />
        ) : null
      ) : schedules.data.length === 0 ? (
        <p className="text-sm text-muted">No standing orders yet.</p>
      ) : (
        <Table caption="Schedules">
          <thead>
            <tr>
              <Th>Schedule</Th>
              <Th>Product</Th>
              <Th>When</Th>
              <Th>Next run</Th>
              <Th>Last run</Th>
              <Th />
            </tr>
          </thead>
          <tbody>
            {schedules.data.map((item) => (
              <tr key={item.id} className={item.enabled ? '' : 'opacity-60'}>
                <Td className="font-medium">
                  {item.name}
                  <div className="text-xs text-muted">{workspaces.label(item.team_id)}</div>
                  {item.notify_on_change && (
                    <p className="mt-2 text-xs font-normal text-muted">
                      {item.last_change_summary ?? 'Change monitoring enabled. Awaiting baseline.'}
                    </p>
                  )}
                  {item.last_change?.previous_report_id && (
                    <Link
                      className="mt-1 block text-xs font-normal underline"
                      to={`/reports/${item.last_change.previous_report_id}`}
                    >
                      Previous compared report
                    </Link>
                  )}
                  {item.question && (
                    <details className="mt-2 text-xs font-normal">
                      <summary className="cursor-pointer">Saved question</summary>
                      <p className="mt-2 whitespace-pre-wrap">{item.question}</p>
                      <p className="mt-1 text-muted">
                        {item.research_mode
                          ? `${item.research_mode} research, ${item.research_languages.join(', ')}, ${item.research_focus}`
                          : 'Existing live evidence'}
                      </p>
                      {item.research_subject && (
                        <p className="mt-1 text-muted">{item.research_subject}</p>
                      )}
                    </details>
                  )}
                </Td>
                <Td className="font-mono text-xs text-muted">
                  {item.template_id}
                  {item.country_iso === null ? '' : ` · ${item.country_iso}`}
                </Td>
                <Td className="text-xs">{describeCadence(item)}</Td>
                <Td className="font-mono text-xs text-muted">{formatUtc(item.next_run_at)}</Td>
                <Td className="text-xs">
                  {item.last_error !== null ? (
                    <span className="text-critical">{item.last_error}</span>
                  ) : item.last_report_id !== null ? (
                    <Link to={`/reports/${item.last_report_id}`} className="hover:underline">
                      Report
                    </Link>
                  ) : (
                    <span className="text-muted">not yet</span>
                  )}
                </Td>
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
      <ScheduleForm
        key={workspaces.key}
        workspaces={workspaces}
        plans={plans}
        templates={templates}
        countries={countries}
        busy={create.busy}
        error={create.error === null ? null : describeError(create.error)}
        onSubmit={(request) => void create.run(request)}
      />
    </div>
  );
}

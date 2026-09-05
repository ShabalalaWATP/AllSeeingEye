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
import { useResource } from '@/lib/hooks/useResource';

import { ScheduleForm, describeCadence } from './ScheduleForm';

/** Standing orders for products, produced by the server as their owner at the chosen hour. */
export function SchedulesSection({
  templates,
  countries,
}: {
  templates: readonly ReportTemplate[];
  countries: readonly Country[];
}) {
  const schedules = useResource(fetchSchedules);
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
                <Td className="font-medium">{item.name}</Td>
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
        templates={templates}
        countries={countries}
        busy={create.busy}
        error={create.error === null ? null : describeError(create.error)}
        onSubmit={(request) => void create.run(request)}
      />
    </div>
  );
}

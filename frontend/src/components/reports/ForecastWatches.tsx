import { useCallback, useState } from 'react';
import { Link } from 'react-router';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SelectField, TextField } from '@/components/ui/Field';
import { Table, Td, Th } from '@/components/ui/Table';
import { forecastCounts, forecastWatches } from '@/lib/api/forecasts';
import { describeError } from '@/lib/api/errors';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { useWorkspaceSelection } from '@/lib/hooks/useWorkspaces';
import type { Workspaces } from '@/lib/hooks/useWorkspaces';

export function OutcomeCounts({ teamId }: { teamId: string }) {
  const [since, setSince] = useState(() => `${new Date().getUTCFullYear()}-01-01`);
  const [until, setUntil] = useState(() =>
    new Date(Date.now() + 86400000).toISOString().slice(0, 10),
  );
  const request = useScopedRequest();
  const load = useCallback(
    () => forecastCounts(teamId, `${since}T00:00:00Z`, `${until}T00:00:00Z`, request()),
    [teamId, since, until, request],
  );
  const resource = useScopedResource(load);
  return (
    <section className="space-y-3" aria-label="Forecast outcome counts">
      <h3 className="font-semibold">Outcome counts by original PHIA band</h3>
      <div className="flex flex-wrap gap-3">
        <TextField
          label="Issued on or after (UTC)"
          type="date"
          required
          value={since}
          onChange={(e) => setSince(e.target.value)}
        />
        <TextField
          label="Issued before (UTC)"
          type="date"
          required
          value={until}
          onChange={(e) => setUntil(e.target.value)}
        />
      </div>
      {resource.loading && <LoadingNote label="Loading forecast outcome counts" />}
      {resource.error && (
        <Alert tone="error">Outcome counts unavailable: {describeError(resource.error)}</Alert>
      )}
      {resource.data && (
        <>
          <p className="text-sm">
            Cohort: {resource.data.since} inclusive to {resource.data.until} exclusive. Counting
            unit: {resource.data.counting_unit}.
          </p>
          {resource.data.forecast_versions === 0 && (
            <p>No forecast versions in this scope and issue-time window.</p>
          )}
          {resource.data.bands.every((row) => row.resolved_denominator === 0) && (
            <p>
              No resolved outcomes in this cohort. An empty or unresolved band has no accuracy
              estimate.
            </p>
          )}
          <div className="overflow-x-auto">
            <Table caption="Forecast versions by likelihood and latest outcome">
              <thead>
                <tr>
                  {[
                    'Original PHIA band',
                    'Resolved true',
                    'Resolved false',
                    'Unresolved',
                    'Open',
                    'Horizon due',
                    'Superseded',
                    'Resolved denominator (true + false)',
                  ].map((label) => (
                    <Th key={label}>{label}</Th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {resource.data.bands.map((row) => (
                  <tr key={row.likelihood}>
                    <Td>{row.likelihood.replaceAll('_', ' ')}</Td>
                    {(
                      [
                        'resolved_true',
                        'resolved_false',
                        'unresolved',
                        'open',
                        'due',
                        'superseded',
                        'resolved_denominator',
                      ] as const
                    ).map((key) => (
                      <Td key={key}>{row[key]}</Td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </Table>
          </div>
          <p className="text-sm text-muted">
            Open means before the outcome horizon; horizon due means it passed without a final
            review. Unresolved means a reviewer could not establish the outcome. Superseded means a
            replacement version was issued. Only resolved true plus false enter the denominator.
          </p>
          <p className="text-sm text-muted">{resource.data.caveat}</p>
        </>
      )}
    </section>
  );
}

function WatchList({ teamId }: { teamId: string }) {
  const [offset, setOffset] = useState(0);
  const request = useScopedRequest();
  const load = useCallback(
    () => forecastWatches(teamId, offset, request()),
    [teamId, offset, request],
  );
  const resource = useScopedResource(load);
  return (
    <div className="space-y-4">
      <p>
        Review reminders use the review date. The outcome becomes due at its separate horizon.
        In-app review does not require email.
      </p>
      {resource.loading && <LoadingNote label="Loading forecast watches" />}
      {resource.error && (
        <Alert tone="error">Forecast watches unavailable: {describeError(resource.error)}</Alert>
      )}
      {resource.data && (
        <>
          {resource.data.items.length === 0 && <p>No forecast watches in this scope.</p>}
          <ul className="space-y-3">
            {resource.data.items.map((row) => (
              <li key={row.ledger_id} className="rounded border border-line p-3">
                <Link
                  className="underline"
                  to={`/reports/${row.report_id}?version=${row.report_version}`}
                >
                  {row.title}, report version {row.report_version}
                </Link>
                <p>
                  {row.review_due ? 'Review due' : 'Review scheduled or completed'}:{' '}
                  {new Date(row.review_at).toLocaleString()}
                </p>
                <p>
                  Outcome state: {row.state}. Horizon: {new Date(row.horizon_end).toLocaleString()}
                </p>
                {row.reminded_at && (
                  <p className="text-xs text-muted">
                    Reminder first raised {new Date(row.reminded_at).toLocaleString()}
                  </p>
                )}
              </li>
            ))}
          </ul>
          {resource.data.total > 20 && (
            <div className="flex gap-2">
              <Button
                variant="secondary"
                disabled={offset === 0}
                onClick={() => setOffset(offset - 20)}
              >
                Previous watches
              </Button>
              <Button
                variant="secondary"
                disabled={offset + 20 >= resource.data.total}
                onClick={() => setOffset(offset + 20)}
              >
                Next watches
              </Button>
            </div>
          )}
        </>
      )}
      <OutcomeCounts key={resource.key} teamId={teamId} />
    </div>
  );
}

export function ForecastWatches({ workspaces }: { workspaces: Workspaces }) {
  const [open, setOpen] = useState(false);
  const selection = useWorkspaceSelection(workspaces);
  return (
    <section className="space-y-4 rounded border border-line p-4" aria-label="Forecast watches">
      <Button variant="secondary" aria-expanded={open} onClick={() => setOpen(!open)}>
        Forecast watches and outcome counts
      </Button>
      {open && (
        <>
          <SelectField
            options={[
              { value: '', label: 'Personal' },
              ...workspaces.teams.map((row) => ({
                value: row.team.id,
                label: `${row.team.name}${row.team.is_active ? '' : ' (archived)'}`,
              })),
            ]}
            label="Forecast workspace"
            value={selection.teamId}
            onChange={(e) => selection.select(e.target.value)}
          />
          {!selection.valid && (
            <Alert tone="error">The selected workspace is no longer accessible.</Alert>
          )}
          {selection.ready && (
            <WatchList key={`${workspaces.key}:${selection.teamId}`} teamId={selection.teamId} />
          )}
        </>
      )}
    </section>
  );
}

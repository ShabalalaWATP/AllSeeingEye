import { Link } from 'react-router';

import { ResearchNavigation } from '@/components/research/ResearchNavigation';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Table, Td, Th } from '@/components/ui/Table';
import { describeError } from '@/lib/api/errors';
import { fetchConflictBoard, fetchDisasterBoard } from '@/lib/api/trackers';
import type { ConflictCard, HazardCard } from '@/lib/api/trackers';
import { useResource } from '@/lib/hooks/useResource';

import { ActivityCells } from './TrackerParts';
import { ConflictMetrics, ConflictCoverageNote } from './ConflictMetrics';
import { ConflictSourceCoverage } from './ConflictSourceCoverage';
import { DailyBriefing } from './DailyBriefing';

const MODULES = [
  {
    to: '/trackers/social',
    title: 'Social',
    blurb: 'Public posts, hashtags and keyword bursts against hourly activity.',
  },
  {
    to: '/trackers/aviation',
    title: 'Aviation',
    blurb: 'Military and unusual flying against baseline, emergencies, GNSS interference.',
  },
  {
    to: '/trackers/maritime',
    title: 'Maritime',
    blurb: 'Broadcast warnings: exercises, closures, security incidents, GNSS notices.',
  },
  {
    to: '/trackers/space',
    title: 'Space',
    blurb: 'Stations overhead, the launch schedule and the geomagnetic picture.',
  },
  {
    to: '/trackers/cyber',
    title: 'Cyber',
    blurb: 'Outage signals, ransomware claims and newly exploited vulnerabilities.',
  },
];

function ConflictBoard({ items }: { items: readonly ConflictCard[] }) {
  return (
    <Table caption="Conflicts">
      <thead>
        <tr>
          <Th>Conflict</Th>
          <Th>Reported activity</Th>
          <Th>Reporting</Th>
          <Th>Latest</Th>
        </tr>
      </thead>
      <tbody>
        {items.map((card) => (
          <tr key={card.conflict.id}>
            <Td>
              <Link
                to={`/trackers/conflicts/${card.conflict.id}`}
                className="font-medium text-text hover:underline"
              >
                {card.conflict.name}
              </Link>
              <div className="font-mono text-xs text-muted">
                {card.conflict.status} · {card.conflict.countries.join(', ')}
              </div>
            </Td>
            <Td>
              <ConflictMetrics card={card} />
            </Td>
            <Td className="font-mono text-xs text-muted">{card.reporting_7d} items / 7 d</Td>
            <Td className="text-xs text-muted">
              {card.latest?.title ?? 'No reports collected in this window'}
            </Td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}

function HazardBoard({ items }: { items: readonly HazardCard[] }) {
  return (
    <ul aria-label="Hazards" className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
      {items.map((card) => (
        <li key={card.hazard} className="rounded-card border border-line bg-surface p-3">
          <div className="flex items-center justify-between gap-2">
            <Link
              to={`/trackers/disasters/${card.hazard}`}
              className="font-medium text-text hover:underline"
            >
              {card.title}
            </Link>
            {card.red_alerts > 0 && (
              <span className="rounded bg-critical/15 px-1.5 py-0.5 font-mono text-[11px] text-critical">
                {card.red_alerts} red
              </span>
            )}
          </div>
          <div className="mt-1">
            <ActivityCells activity={card.activity} />
          </div>
          {card.countries.length > 0 && (
            <div className="mt-1 font-mono text-xs text-muted">{card.countries.join(' ')}</div>
          )}
          <p className="mt-2 text-xs text-muted">{card.top?.title ?? 'Quiet this week'}</p>
        </li>
      ))}
    </ul>
  );
}

export default function TrackersPage() {
  const conflicts = useResource(fetchConflictBoard);
  const disasters = useResource(fetchDisasterBoard);
  return (
    <section className="flex h-full flex-col gap-6 overflow-y-auto p-6">
      <ResearchNavigation />
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold">Live monitor</h1>
          <p className="mt-1 text-sm text-muted">
            Daily analysis, with the latest collected activity below.
          </p>
        </div>
        <Link to="/subscriptions" className="text-sm text-ember hover:underline">
          Create a subscription
        </Link>
      </header>
      <DailyBriefing />
      <div className="flex flex-col gap-3">
        <h2 className="text-base font-semibold">Conflicts</h2>
        <ConflictCoverageNote />
        {conflicts.error === null ? null : (
          <Alert tone="error">{describeError(conflicts.error)}</Alert>
        )}
        {conflicts.data === null ? (
          conflicts.loading ? (
            <LoadingNote label="Loading conflicts" />
          ) : null
        ) : (
          <ConflictBoard items={conflicts.data} />
        )}
      </div>
      <details>
        <summary className="w-fit cursor-pointer text-sm text-muted hover:text-text">
          Inspect conflict source coverage
        </summary>
        <div className="mt-3">
          <ConflictSourceCoverage />
        </div>
      </details>
      <div className="flex flex-col gap-3">
        <h2 className="text-base font-semibold">Global disasters</h2>
        {disasters.error === null ? null : (
          <Alert tone="error">{describeError(disasters.error)}</Alert>
        )}
        {disasters.data === null ? (
          disasters.loading ? (
            <LoadingNote label="Loading hazards" />
          ) : null
        ) : (
          <HazardBoard items={disasters.data} />
        )}
      </div>
      <nav aria-label="Specialist monitoring" className="border-t border-line pt-5">
        <h2 className="mb-3 text-base font-semibold">Explore connected feeds</h2>
        <ul aria-label="Modules" className="grid gap-x-6 gap-y-4 md:grid-cols-2 xl:grid-cols-5">
          {MODULES.map((module) => (
            <li key={module.to}>
              <Link
                to={module.to}
                className="font-medium text-text hover:text-ember hover:underline"
              >
                {module.title}
              </Link>
              <p className="mt-1 text-xs leading-5 text-muted">{module.blurb}</p>
            </li>
          ))}
        </ul>
      </nav>
    </section>
  );
}

import { Link } from 'react-router';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Table, Td, Th } from '@/components/ui/Table';
import { fetchAviationBoard } from '@/lib/api/aviation';
import type { AreaActivity, CountryActivity } from '@/lib/api/aviation';
import { describeError } from '@/lib/api/errors';
import { formatUtc } from '@/lib/format';
import { useResource } from '@/lib/hooks/useResource';

import { BackToTrackers, EventRow, ShowOnGlobe } from './TrackerParts';

/** The count against its baseline in words: rising, steady, quiet or no baseline yet. */
export function describeRatio(ratio: number | null): string {
  if (ratio === null) return 'no baseline';
  if (ratio >= 1.5) return 'above baseline';
  if (ratio <= 0.5) return 'below baseline';
  return 'steady';
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-card border border-line bg-surface px-3 py-2">
      <div className="font-mono text-[11px] uppercase tracking-wide text-muted">{label}</div>
      <div className="text-lg font-semibold tabular-nums">{value}</div>
    </div>
  );
}

function CountryRows({ rows }: { rows: readonly CountryActivity[] }) {
  return (
    <Table caption="Military aircraft by nation">
      <thead>
        <tr>
          <Th>Nation</Th>
          <Th>Now</Th>
          <Th>Baseline</Th>
          <Th>Against baseline</Th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.iso}>
            <Td className="font-mono">{row.iso}</Td>
            <Td className="font-mono tabular-nums">{row.count}</Td>
            <Td className="font-mono tabular-nums text-muted">
              {row.baseline === null ? '' : row.baseline.toFixed(1)}
            </Td>
            <Td className={row.ratio !== null && row.ratio >= 1.5 ? 'text-critical' : 'text-muted'}>
              {describeRatio(row.ratio)}
            </Td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}

function AreaRows({ rows }: { rows: readonly AreaActivity[] }) {
  return (
    <Table caption="Watched areas">
      <thead>
        <tr>
          <Th>Area</Th>
          <Th>Aircraft</Th>
          <Th>Military</Th>
          <Th>Baseline</Th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.id}>
            <Td>{row.name}</Td>
            <Td className="font-mono tabular-nums">{row.count}</Td>
            <Td className="font-mono tabular-nums">{row.military}</Td>
            <Td className="font-mono tabular-nums text-muted">
              {row.baseline === null ? '' : row.baseline.toFixed(1)}
            </Td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}

export default function AviationPage() {
  const { data, error, loading } = useResource(fetchAviationBoard);
  if (data === null) {
    return (
      <section className="p-6">
        {error === null ? null : <Alert tone="error">{describeError(error)}</Alert>}
        {loading ? <LoadingNote label="Loading aviation" /> : null}
      </section>
    );
  }
  return (
    <article className="flex h-full flex-col gap-5 overflow-y-auto p-6">
      <header className="flex flex-col gap-2">
        <BackToTrackers />
        <h1 className="text-xl font-semibold">Aviation</h1>
        <p className="text-sm text-muted">
          Military and unusual flying tracked now against the last month, from volunteer ADS-B
          receivers, with emergencies and where satellite positioning looks degraded.
        </p>
        <div className="grid gap-2 sm:grid-cols-3 lg:grid-cols-6">
          <Stat label="Military" value={data.military_total} />
          <Stat label="Interesting" value={data.interesting} />
          <Stat label="LADD" value={data.ladd} />
          <Stat label="PIA" value={data.pia} />
          <Stat label="Emergencies" value={data.emergencies.length} />
          <Stat
            label="Jam cells"
            value={`${String(data.jam_red)} red, ${String(data.jam_amber)} amber`}
          />
        </div>
        {data.jam_updated_at !== null && (
          <p className="font-mono text-xs text-muted">
            Interference map updated {formatUtc(data.jam_updated_at)}
          </p>
        )}
        <div className="flex flex-wrap gap-2">
          <ShowOnGlobe country={null} />
          <Link
            to="/reports?template=aviation_activity"
            className="rounded-md border border-line bg-surface-2 px-3 py-2 text-sm text-text hover:bg-surface"
          >
            Generate activity report
          </Link>
        </div>
      </header>
      {data.emergencies.length > 0 && (
        <section aria-label="Emergencies" className="flex flex-col gap-1">
          <h2 className="text-base font-semibold text-critical">Emergency squawks</h2>
          <ul>
            {data.emergencies.map((event) => (
              <EventRow key={event.id} event={event} />
            ))}
          </ul>
        </section>
      )}
      <section aria-label="By nation" className="flex flex-col gap-2">
        <h2 className="text-base font-semibold">Military aircraft by nation</h2>
        {data.by_country.length === 0 ? (
          <p className="text-sm text-muted">No military aircraft are being tracked right now.</p>
        ) : (
          <CountryRows rows={data.by_country} />
        )}
      </section>
      <section aria-label="Watched areas" className="flex flex-col gap-2">
        <h2 className="text-base font-semibold">Watched areas</h2>
        <AreaRows rows={data.areas} />
      </section>
    </article>
  );
}

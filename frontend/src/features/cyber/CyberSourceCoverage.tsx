import type { CyberSnapshot } from '@/lib/api/cyber';
import { SourceLink } from '@/components/ui/SourceLink';
import { formatUtc } from '@/lib/format';

export function CyberSourceCoverage({ data }: { data: CyberSnapshot }) {
  const healthy = data.sources.filter((source) => source.status === 'healthy').length;
  return (
    <details className="border-t border-line pt-5 text-xs leading-6 text-muted">
      <summary className="w-fit cursor-pointer font-medium hover:text-text">
        Source coverage · {healthy}/{data.sources.length} feeds healthy
      </summary>
      <p className="mt-3 max-w-4xl">{data.coverage_note}</p>
      <p className="mt-2 max-w-4xl">
        Multiple records may describe the same event or repeat one publisher. Counts describe
        collected reporting, not independently confirmed incidents. Recent provider success does not
        guarantee complete coverage.
      </p>
      <ul className="mt-4 grid gap-x-8 gap-y-4 md:grid-cols-2">
        {data.sources.map((source) => (
          <li key={source.source_id} className="border-t border-line py-3">
            <div className="flex flex-wrap justify-between gap-2">
              <SourceLink url={source.url}>{source.name}</SourceLink>
              <span className={source.status === 'degraded' ? 'text-amber' : ''}>
                {source.status}
              </span>
            </div>
            <p>{source.retained_count} dated records in this period</p>
            <p>Last successful collection: {formatUtc(source.last_success)}</p>
            {source.last_error_at && (
              <p>Last collection error: {formatUtc(source.last_error_at)}</p>
            )}
          </li>
        ))}
      </ul>
    </details>
  );
}

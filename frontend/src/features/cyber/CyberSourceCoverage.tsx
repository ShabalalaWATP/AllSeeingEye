import type { CyberSnapshot } from '@/lib/api/cyber';
import { SourceLink } from '@/components/ui/SourceLink';
import { formatUtc } from '@/lib/format';

const STATUS_STYLE: Record<CyberSnapshot['sources'][number]['status'], string> = {
  healthy: 'text-good',
  degraded: 'text-amber',
  idle: 'text-muted',
  disabled: 'text-critical',
};

export function CyberSourceCoverage({ data }: { data: CyberSnapshot }) {
  const healthy = data.sources.filter((source) => source.status === 'healthy').length;
  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold">
        Source coverage{' '}
        <span className="font-normal text-muted">
          · {healthy}/{data.sources.length} feeds healthy
        </span>
      </h3>
      <p className="max-w-4xl text-xs leading-5 text-muted">{data.coverage_note}</p>
      <p className="max-w-4xl text-xs leading-5 text-muted">
        Multiple records may describe the same event or repeat one publisher. Counts describe
        collected reporting, not independently confirmed incidents. Recent provider success does not
        guarantee complete coverage.
      </p>
      <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {data.sources.map((source) => (
          <li
            key={source.source_id}
            className="rounded-lg border border-line/60 bg-surface/50 px-3 py-2.5 text-xs leading-5"
          >
            <div className="flex items-start justify-between gap-2">
              <span className="min-w-0 truncate">
                <SourceLink url={source.url}>{source.name}</SourceLink>
              </span>
              <span
                className={`inline-flex shrink-0 items-center gap-1.5 ${STATUS_STYLE[source.status]}`}
              >
                <span aria-hidden="true" className="size-1.5 rounded-full bg-current" />
                {source.status}
              </span>
            </div>
            <p className="text-muted">
              {source.retained_count.toLocaleString('en-GB')} dated records · last success{' '}
              {formatUtc(source.last_success)}
            </p>
            {source.last_error_at && (
              <p className="text-muted">Last collection error {formatUtc(source.last_error_at)}</p>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

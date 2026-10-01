import { PageHeader } from '@/components/ui/PageHeader';
import { Button } from '@/components/ui/Button';
import { AutomaticBriefingNote } from '@/components/research/AutomaticBriefingNote';
import { CYBER_PERIODS, type CyberDays, type CyberSnapshot } from '@/lib/api/cyber';
import { formatUtc } from '@/lib/format';

export function CyberHeader({
  days,
  onDays,
  data,
  loading,
  onRefresh,
  onOpenMap,
}: {
  days: CyberDays;
  onDays: (days: CyberDays) => void;
  data: CyberSnapshot | null;
  loading: boolean;
  onRefresh: () => void;
  onOpenMap: () => void;
}) {
  const healthy = data?.sources.filter((source) => source.status === 'healthy').length ?? 0;
  return (
    <header className="relative overflow-hidden rounded-2xl border border-line/70 bg-surface/50 px-5 py-6 sm:px-7">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(60%_80%_at_100%_0%,color-mix(in_srgb,var(--color-cyan)_14%,transparent),transparent_70%)]"
      />
      <div className="relative flex flex-wrap items-end justify-between gap-5">
        <PageHeader
          as="div"
          title="Cyber intelligence"
          eyebrow="Monitoring"
          eyebrowTone="cyan"
          description="Collected reporting, exploitation, criminal claims and connectivity signals from public sources, read through themed lenses and an AI assessment that cites its evidence. Counts describe collected reporting, never total attacks."
        >
          {data && (
            <dl className="mt-2 flex flex-wrap gap-x-5 gap-y-2 text-xs text-muted">
              <div className="inline-flex items-center gap-2">
                <span aria-hidden="true" className="size-1.5 rounded-full bg-good" />
                <dt className="sr-only">Snapshot time</dt>
                <dd>Snapshot {formatUtc(data.as_of)}</dd>
              </div>
              <div>
                <dt className="sr-only">Evidence window</dt>
                <dd>
                  {formatUtc(data.period_from)} to {formatUtc(data.period_to)}
                </dd>
              </div>
              <div>
                <dt className="sr-only">Feed health</dt>
                <dd>
                  {healthy}/{data.sources.length} feeds healthy
                </dd>
              </div>
            </dl>
          )}
        </PageHeader>
        <div className="flex flex-col items-start gap-3 sm:items-end">
          <div
            role="group"
            aria-label="Choose cyber reporting period"
            className="flex rounded-lg border border-line/70 bg-ground/60 p-1"
          >
            {CYBER_PERIODS.map((period) => (
              <button
                key={period}
                type="button"
                aria-pressed={days === period}
                onClick={() => onDays(period)}
                className={`min-h-9 min-w-14 rounded-md px-3 text-xs font-medium transition-colors ${
                  days === period
                    ? 'bg-ember text-ground shadow-sm'
                    : 'text-muted hover:bg-surface-2 hover:text-text'
                }`}
              >
                {period} days
              </button>
            ))}
          </div>
          <AutomaticBriefingNote
            subject="Choosing a period"
            className="max-w-sm text-xs leading-5 text-muted sm:text-right"
          />
          <div className="flex flex-wrap gap-2">
            <Button variant="secondary" onClick={onRefresh} busy={loading}>
              Refresh sources
            </Button>
            <Button onClick={onOpenMap}>Open cyber map</Button>
          </div>
        </div>
      </div>
    </header>
  );
}

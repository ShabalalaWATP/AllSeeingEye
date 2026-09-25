import { SourceLink } from '@/components/ui/SourceLink';
import { Button } from '@/components/ui/Button';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import type { EconomyNewsItem } from '@/lib/api/economy';
import type { EconomyBriefing, EconomyDays } from '@/lib/api/economyBriefing';
import type { Report } from '@/lib/api/reports';
import { formatUtc } from '@/lib/format';
import { EconomyNewsOverview } from './EconomyNewsOverview';
import { REGIONS, type RegionCode } from './economyPresentation';

const viewpoints = {
  official_issuer: 'Official release',
  state_aligned: 'State-affiliated source',
  publisher: 'News reporting',
};
const newsDate = (value: string) =>
  new Intl.DateTimeFormat('en-GB', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'UTC',
  }).format(new Date(value));

export function EconomyNewsPanel({
  items,
  loading,
  error,
  region,
  coverage,
  days,
  asOf,
  considered,
  passed,
  report,
  briefing,
  explainerLeads = false,
  onRetry,
}: {
  items: readonly EconomyNewsItem[];
  loading: boolean;
  error: string | null;
  region: RegionCode;
  coverage?: string | undefined;
  days: EconomyDays;
  asOf?: string | undefined;
  considered?: number | undefined;
  passed?: number | undefined;
  report: Report | null;
  briefing: EconomyBriefing | null;
  explainerLeads?: boolean;
  onRetry: () => void;
}) {
  const filtered = (
    region === 'WORLD' ? items : items.filter((item) => item.region_codes.includes(region))
  ).slice(0, region === 'WORLD' ? 6 : 8);
  const title =
    region === 'WORLD'
      ? 'Worldwide economic news'
      : `${REGIONS.find((item) => item.id === region)?.name ?? region} reporting`;
  return (
    <section aria-label={title} className="space-y-4">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold">{title}</h2>
        <span className="font-mono text-2xs uppercase tracking-wider text-muted">
          Past {days} days · UTC
        </span>
      </header>
      {asOf && (
        <p className="text-xs text-muted">
          News window: {formatUtc(new Date(Date.parse(asOf) - days * 86_400_000).toISOString())} to{' '}
          {formatUtc(asOf)}
        </p>
      )}
      <EconomyNewsOverview
        items={filtered}
        region={region}
        report={report}
        briefing={briefing}
        explainerLeads={explainerLeads}
      />
      {loading && items.length === 0 && <LoadingNote label="Collecting economic headlines" />}
      {error && (
        <Alert tone="error">
          {error}{' '}
          <Button variant="ghost" onClick={onRetry}>
            Retry news
          </Button>
        </Alert>
      )}
      {!loading && !error && considered !== undefined && considered > 0 && (
        <p className="text-xs text-muted">
          {considered} headline{considered === 1 ? '' : 's'} reached this window;{' '}
          {passed ?? filtered.length} carried economic substance. The rest were business-section
          features rather than economic reporting.
        </p>
      )}
      {!loading && !error && filtered.length === 0 && (
        <p className="border-y border-line py-6 text-sm text-muted">
          No substantial economic reporting in this window for this focus. This is a coverage gap,
          not evidence of an unchanged economy.
        </p>
      )}
      {filtered.length > 0 && (
        <ol className="grid gap-x-8 md:grid-cols-2 xl:grid-cols-3">
          {filtered.map((item) => (
            <li
              key={item.id}
              className="flex flex-col justify-between gap-3 border-t border-line py-4"
            >
              <div className="text-sm font-medium leading-6">
                <SourceLink url={item.url}>{item.title}</SourceLink>
              </div>
              <div className="text-[11px] leading-5 text-muted">
                <span>{item.source_name}</span>
                <span className="mx-2">·</span>
                <time dateTime={item.published_at}>{newsDate(item.published_at)}</time>
                <p className="mt-1 text-[11px] text-muted">{item.relevance}</p>
                <p className={item.viewpoint === 'state_aligned' ? 'text-amber' : ''}>
                  {viewpoints[item.viewpoint]}
                </p>
              </div>
            </li>
          ))}
        </ol>
      )}
      {coverage && (
        <details className="text-xs leading-5 text-muted">
          <summary className="w-fit cursor-pointer hover:text-text">News coverage</summary>
          <p className="mt-2 max-w-4xl">{coverage}</p>
        </details>
      )}
    </section>
  );
}

import { useState } from 'react';
import type { EconomyRegion } from '@/lib/api/economy';
import { SourceLink } from '@/components/ui/SourceLink';
import { EconomicChart } from './EconomicChart';
import { CountryIndicators } from './CountryIndicators';
import { CountryInsights } from './CountryInsights';
import { CountryOverview } from './CountryOverview';
import { latestObservation, metricExplanation } from './economyPresentation';

export function CountryEconomy({ region }: { region: EconomyRegion | undefined }) {
  const [choice, setChoice] = useState<string | null>(null);
  if (!region)
    return (
      <p className="text-sm text-muted">
        Official indicators for this region are currently unavailable.
      </p>
    );
  const series = region.series.find((item) => item.id === choice) ?? region.series[0];
  const observations = region.series.flatMap((item) => {
    const point = latestObservation(item);
    return point ? [point.date] : [];
  });
  const years = [...new Set(observations)].sort();
  const cached = region.series.filter((item) => item.status === 'stale').length;
  return (
    <section aria-label={`${region.name} economic indicators`} className="space-y-6">
      <header className="flex flex-wrap items-baseline justify-between gap-3">
        <h3 className="text-lg font-semibold">Economic fundamentals</h3>
        <span className="font-mono text-[10px] uppercase tracking-wider text-muted">
          Annual official indicators
        </span>
      </header>
      <CountryOverview region={region} />
      <div className="flex flex-wrap gap-x-6 gap-y-2 border-l-2 border-ember pl-4 text-xs leading-5 text-muted">
        <span>
          <strong className="font-mono font-medium text-text">
            {observations.length}/{region.series.length}
          </strong>{' '}
          indicators have observations
        </span>
        <span>
          {years.length
            ? `Latest observations: ${years.length === 1 ? years[0] : `${years[0]} to ${years.at(-1)}`}`
            : 'No observation period available'}
        </span>
        {cached > 0 && <span>{cached} series served from an older cache</span>}
      </div>
      <p className="text-xs leading-5 text-muted">
        Every available history loads automatically. Select an indicator to explore exact values and
        its methodology. Changes marked pp are percentage points, not percentage growth.
      </p>
      <CountryIndicators region={region} selected={series?.id} onSelect={setChoice} />
      {series && (
        <div className="grid gap-8 xl:grid-cols-[minmax(0,1fr)_240px]">
          <EconomicChart key={`${region.id}:${series.id}`} series={series} />
          <aside className="space-y-4 text-sm leading-6 text-muted">
            <h4 className="font-semibold text-text">{series.name}</h4>
            <p>{metricExplanation(series.id)}</p>
            <p>{series.note}</p>
            <dl className="space-y-3 text-xs">
              <div>
                <dt>Provider</dt>
                <dd className="text-text">{series.provider}</dd>
              </div>
              <div>
                <dt>Unit</dt>
                <dd className="text-text">{series.unit}</dd>
              </div>
              {series.source_updated_at && (
                <div>
                  <dt>Provider publication</dt>
                  <dd className="font-mono text-text">{series.source_updated_at}</dd>
                </div>
              )}
            </dl>
            <SourceLink url={series.source_url}>View original data</SourceLink>
          </aside>
        </div>
      )}
      <CountryInsights region={region} />
    </section>
  );
}

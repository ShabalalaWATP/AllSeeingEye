import { useState } from 'react';
import type { EconomyRegion } from '@/lib/api/economy';
import { SourceLink } from '@/components/ui/SourceLink';
import { EconomicChart } from './EconomicChart';
import { formatEconomicValue, latestObservation, metricExplanation } from './economyPresentation';

export function CountryEconomy({ region }: { region: EconomyRegion | undefined }) {
  const [choice, setChoice] = useState<string | null>(null);
  if (!region)
    return (
      <p className="text-sm text-muted">
        Official indicators for this region are currently unavailable.
      </p>
    );
  const series = region.series.find((item) => item.id === choice) ?? region.series[0];
  return (
    <section aria-label={`${region.name} economic indicators`} className="space-y-6">
      <header className="flex flex-wrap items-baseline justify-between gap-3">
        <h3 className="text-lg font-semibold">Economic fundamentals</h3>
        <span className="font-mono text-[10px] uppercase tracking-wider text-muted">
          Annual official indicators
        </span>
      </header>
      <div className="grid grid-cols-2 divide-x divide-line border-y border-line md:grid-cols-4">
        {region.series.map((item) => {
          const latest = latestObservation(item);
          return (
            <button
              key={item.id}
              type="button"
              aria-pressed={series?.id === item.id}
              onClick={() => setChoice(item.id)}
              className={`min-h-32 min-w-0 px-3 py-5 text-left transition-colors hover:bg-surface-2 sm:px-5 ${series?.id === item.id ? 'bg-surface-2' : ''}`}
            >
              <span className="block text-xs text-muted">{item.name}</span>
              <span
                className={`mt-2 block break-words font-mono text-xl sm:text-2xl ${series?.id === item.id ? 'text-ember' : 'text-text'}`}
              >
                {formatEconomicValue(latest?.value ?? null, item.unit)}
              </span>
              <span className="mt-2 block text-[10px] text-muted">
                {latest ? `Observation: ${latest.date}` : 'No published observation'}
                {item.status === 'stale' ? ' · cached' : ''}
              </span>
            </button>
          );
        })}
      </div>
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
    </section>
  );
}

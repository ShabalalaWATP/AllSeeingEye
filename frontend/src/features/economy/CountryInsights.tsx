import type { EconomyRegion } from '@/lib/api/economy';
import { SourceLink } from '@/components/ui/SourceLink';
import { countryInsights } from './economicChanges';

export function CountryInsights({ region }: { region: EconomyRegion }) {
  const insights = countryInsights(region);
  return (
    <section
      aria-label={`${region.name} calculated insights`}
      className="border-y border-line py-6"
    >
      <header className="mb-5 flex flex-wrap items-baseline justify-between gap-2">
        <h4 className="text-base font-semibold">What the data shows</h4>
        <span className="text-[10px] uppercase tracking-wider text-muted">
          Calculated from published observations
        </span>
      </header>
      {insights.length ? (
        <div className="grid gap-x-8 gap-y-6 sm:grid-cols-2">
          {insights.map((insight) => (
            <div key={insight.title} className="space-y-2">
              <h5 className="text-xs font-semibold uppercase tracking-wider text-text">
                {insight.title}
              </h5>
              <p className="text-sm leading-6 text-muted">{insight.text}</p>
              <SourceLink url={insight.series.source_url}>
                Source: {insight.series.provider}
              </SourceLink>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm leading-6 text-muted">
          There are not enough published observations for a country readout. Missing data does not
          imply a stable economy.
        </p>
      )}
      <p className="mt-5 text-xs leading-5 text-muted">
        These are historical descriptions, not forecasts or investment recommendations. Indicator
        years and government coverage may differ.
      </p>
    </section>
  );
}

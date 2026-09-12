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
      <header className="mb-5 space-y-2">
        <h4 className="text-base font-semibold">What the data shows</h4>
        <p className="max-w-3xl text-sm leading-6 text-muted">
          Read the recorded result first, then its meaning. These observations explain the annual
          economic backdrop; they do not describe changes during the selected news summary period.
        </p>
      </header>
      {insights.length ? (
        <div className="grid gap-x-8 gap-y-6 sm:grid-cols-2">
          {insights.map((insight) => (
            <article key={insight.title} className="space-y-3 border-t border-line pt-4">
              <h5 className="text-xs font-semibold uppercase tracking-wider text-text">
                {insight.title}
              </h5>
              <p className="text-sm font-medium leading-6 text-text">{insight.text}</p>
              <p className="text-sm leading-6 text-muted">{insight.explanation}</p>
              <div className="text-xs">
                <SourceLink url={insight.series.source_url}>
                  Source: {insight.series.provider}
                </SourceLink>
                {insight.series.status === 'stale' && (
                  <span className="text-muted"> · Cached source data</span>
                )}
              </div>
            </article>
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

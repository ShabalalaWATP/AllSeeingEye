import type { EconomyRegion } from '@/lib/api/economy';
import { SourceLink } from '@/components/ui/SourceLink';
import { countryOverview } from './countryOverviewData';

export function CountryOverview({ region }: { region: EconomyRegion }) {
  const overview = countryOverview(region);
  return (
    <section aria-label={`${region.name} economic overview`} className="max-w-4xl space-y-3">
      <h4 className="text-xs font-semibold uppercase tracking-wider text-muted">
        {region.name} at a glance
      </h4>
      <p className="text-base leading-7 text-text">
        {overview.text ||
          'There are too few published observations to summarise growth, prices, employment or the external balance. Explore the available indicators below.'}
      </p>
      <p className="text-xs leading-5 text-muted">
        Historical context from annual observations, separate from the selected news summary period.
        {overview.hasOlderObservations && ' Some observations are more than two years old.'}
        {overview.cached && ' Some source data is being served from an older cache.'}
      </p>
      {overview.sources.length > 0 && (
        <ul aria-label="Overview sources" className="flex flex-wrap gap-x-5 gap-y-2 text-xs">
          {overview.sources.map((source) => (
            <li key={source.id}>
              <SourceLink url={source.url}>
                {source.label}: {source.provider}
              </SourceLink>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

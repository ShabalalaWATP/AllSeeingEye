import type { EconomyRegion, EconomySeries } from '@/lib/api/economy';
import type { ExplainerGlossaryEntry } from '@/lib/api/economyExplainer';
import { annualChange, formatAnnualChange, observationAge } from './economicChanges';
import { formatEconomicValue, latestObservation } from './economyPresentation';
import { IndicatorMeaning } from './IndicatorMeaning';
import { IndicatorSparkline } from './IndicatorSparkline';

const GROUPS = [
  { name: 'Output and living standards', ids: ['gdp', 'growth', 'gdp_per_capita', 'population'] },
  { name: 'Prices and employment', ids: ['inflation', 'unemployment'] },
  { name: 'Trade and industry', ids: ['exports', 'imports', 'current_account', 'manufacturing'] },
  { name: 'Public finances and investment', ids: ['government_debt', 'investment'] },
];
const knownIds = new Set(GROUPS.flatMap((group) => group.ids));

export function CountryIndicators({
  region,
  selected,
  onSelect,
  glossary = [],
}: {
  region: EconomyRegion;
  selected: string | undefined;
  onSelect: (id: string) => void;
  glossary?: readonly ExplainerGlossaryEntry[];
}) {
  const groups = [
    ...GROUPS.map((group) => ({
      ...group,
      items: group.ids.flatMap((id) => {
        const item = region.series.find((series) => series.id === id);
        return item ? [item] : [];
      }),
    })),
    {
      name: 'Other official indicators',
      items: region.series.filter((series) => !knownIds.has(series.id)),
    },
  ];
  return (
    <div className="space-y-5">
      {groups
        .filter((group) => group.items.length > 0)
        .map((group) => (
          <div key={group.name}>
            <h4 className="mb-2 text-2xs font-semibold uppercase tracking-[0.16em] text-muted">
              {group.name}
            </h4>
            <div
              className={`grid grid-cols-2 border-t border-l border-line ${group.items.length > 2 ? 'lg:grid-cols-4' : ''}`}
            >
              {group.items.map((item) => (
                <div
                  key={item.id}
                  className={`flex min-w-0 flex-col border-r border-b border-line ${selected === item.id ? 'bg-surface-2' : ''}`}
                >
                  <IndicatorButton
                    series={item}
                    selected={selected === item.id}
                    onSelect={onSelect}
                  />
                  <IndicatorMeaning series={item} glossary={glossary} />
                </div>
              ))}
            </div>
          </div>
        ))}
    </div>
  );
}

function IndicatorButton({
  series,
  selected,
  onSelect,
}: {
  series: EconomySeries;
  selected: boolean;
  onSelect: (id: string) => void;
}) {
  const latest = latestObservation(series);
  const change = annualChange(series);
  const age = latest ? observationAge(latest.date) : '';
  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={() => onSelect(series.id)}
      className="min-w-0 flex-1 px-3 py-4 text-left transition-colors hover:bg-surface-2 focus-visible:outline-2 focus-visible:outline-ember sm:px-4"
    >
      <span className="block min-h-8 text-xs leading-4 text-muted">{series.name}</span>
      <span
        className={`block break-words font-mono text-xl sm:text-2xl ${selected ? 'text-ember' : 'text-text'}`}
      >
        {formatEconomicValue(latest?.value ?? null, series.unit)}
      </span>
      <span className="mt-1 block min-h-4 text-2xs text-muted">{series.unit}</span>
      <IndicatorSparkline series={series} />
      <span className="mt-2 block text-2xs leading-4 text-muted">
        {latest ? `Observation: ${latest.date}` : 'No published observation'}
        {age ? ` · ${age}` : ''}
        {series.status === 'stale' ? ' · cached' : ''}
      </span>
      <span className="mt-1 block text-2xs leading-4 text-muted">
        {change ? formatAnnualChange(change) : 'Annual change unavailable'}
      </span>
    </button>
  );
}

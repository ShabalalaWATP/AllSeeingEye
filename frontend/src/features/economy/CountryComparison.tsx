import { useState } from 'react';
import { SelectField } from '@/components/ui/Field';
import { SourceLink } from '@/components/ui/SourceLink';
import type { EconomyRegion } from '@/lib/api/economy';
import { compareCountries } from './comparisonData';
import { formatEconomicValue, metricExplanation } from './economyPresentation';

export function CountryComparison({
  regions,
  focus,
}: {
  regions: readonly EconomyRegion[];
  focus: string;
}) {
  const [metric, setMetric] = useState('growth');
  const [year, setYear] = useState('');
  const options = [
    ...new Map(
      regions.flatMap((region) => region.series.map((item) => [item.id, item] as const)),
    ).values(),
  ];
  const comparison = compareCountries(regions, metric, year);
  const { definition, selected, rows, ranked } = comparison;
  if (!definition)
    return <p className="text-sm text-muted">Country comparison data is currently unavailable.</p>;
  const low = Math.min(0, ...ranked.map((row) => row.value));
  const high = Math.max(0, ...ranked.map((row) => row.value));
  const span = high - low || 1;
  const zero = (-low / span) * 100;
  const highest = ranked[0],
    lowest = ranked[ranked.length - 1];
  return (
    <section aria-label="Compare economies" className="space-y-6 border-y border-line py-7">
      <header className="flex flex-wrap items-end justify-between gap-5">
        <div>
          <h2 className="text-xl font-semibold">Compare economies</h2>
          <p className="mt-2 max-w-2xl text-sm text-muted">
            Compare the same indicator in the same year. The default uses the most complete recent
            period.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <SelectField
            label="Comparison indicator"
            value={metric}
            onChange={(event) => {
              setMetric(event.target.value);
              setYear('');
            }}
            options={options.map((item) => ({ value: item.id, label: item.name }))}
          />
          <SelectField
            label="Comparison year"
            value={selected?.year ?? ''}
            onChange={(event) => setYear(event.target.value)}
            options={
              comparison.years.length
                ? comparison.years.map((period) => ({
                    value: period.year,
                    label: `${period.year} (${period.count}/${rows.length} countries)`,
                  }))
                : [{ value: '', label: 'No shared observations' }]
            }
          />
        </div>
      </header>
      <div className="grid gap-8 xl:grid-cols-[minmax(0,1fr)_280px]">
        <div
          className="space-y-4"
          aria-label={`${definition.name} comparison for ${selected?.year ?? 'unknown year'}`}
        >
          {rows.map((row) => (
            <div
              key={row.id}
              className={`grid grid-cols-[110px_minmax(0,1fr)] items-center gap-3 text-xs sm:grid-cols-[140px_minmax(0,1fr)_100px] ${row.id === focus ? 'text-ember' : 'text-text'}`}
            >
              <span>{row.name}</span>
              <div aria-hidden="true" className="relative h-7 bg-surface-2/50">
                <span
                  className="absolute inset-y-0 border-l border-muted/60"
                  style={{ left: `${zero}%` }}
                />
                {row.value !== null && (
                  <span
                    className={`absolute inset-y-1 min-w-px ${row.id === focus ? 'bg-ember' : 'bg-muted/70'}`}
                    style={{
                      left: `${((Math.min(0, row.value) - low) / span) * 100}%`,
                      width: `${(Math.abs(row.value) / span) * 100}%`,
                    }}
                  />
                )}
              </div>
              <span className="col-start-2 font-mono sm:col-auto sm:text-right">
                {formatEconomicValue(row.value, definition.unit)}
              </span>
            </div>
          ))}
        </div>
        <aside className="space-y-3 text-sm leading-6 text-muted">
          <h3 className="font-semibold text-text">What the comparison shows</h3>
          {highest && lowest && ranked.length > 1 ? (
            <p>
              {highest.value === lowest.value ? (
                `The ${ranked.length} available countries report the same value in ${selected?.year}.`
              ) : (
                <>
                  Among {ranked.length} available countries in {selected?.year}, {highest.name} has
                  the highest recorded value ({formatEconomicValue(highest.value, definition.unit)})
                  and {lowest.name} the lowest ({formatEconomicValue(lowest.value, definition.unit)}
                  ).
                </>
              )}
            </p>
          ) : (
            <p>There are too few observations for a country ranking in this period.</p>
          )}
          {comparison.world !== null && (
            <p>
              Worldwide reference for {selected?.year}:{' '}
              <strong className="font-mono text-text">
                {formatEconomicValue(comparison.world, definition.unit)}
              </strong>
              . This is the provider’s world aggregate, not an average of these five countries.
            </p>
          )}
          <p>{metricExplanation(metric)}</p>
          <p className="text-xs">
            A higher value is not automatically better. Revisions, reporting coverage and national
            definitions can affect comparisons.
          </p>
        </aside>
      </div>
      <details className="text-xs text-muted">
        <summary className="w-fit cursor-pointer py-2 hover:text-text">
          Comparison data and sources
        </summary>
        <div className="overflow-x-auto">
          <table className="mt-3 w-full min-w-[420px] text-left">
            <caption className="sr-only">
              {definition.name} country comparison, {definition.unit}
            </caption>
            <thead>
              <tr>
                <th className="py-3">Country</th>
                <th>{selected?.year ?? 'Selected year'}</th>
                <th>Previous year</th>
                <th>Source</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id} className="border-t border-line">
                  <td className="py-3">{row.name}</td>
                  <td className="font-mono">{formatEconomicValue(row.value, definition.unit)}</td>
                  <td className="font-mono">
                    {formatEconomicValue(row.previous, definition.unit)}
                  </td>
                  <td>
                    {row.series && (
                      <SourceLink url={row.series.source_url}>
                        {row.series.provider}
                        {row.series.status === 'stale' ? ' (cached)' : ''}
                      </SourceLink>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </section>
  );
}

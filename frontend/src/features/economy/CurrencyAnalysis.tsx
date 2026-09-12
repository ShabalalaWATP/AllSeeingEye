import { useState } from 'react';
import type { EconomySeries } from '@/lib/api/economy';
import { SelectField } from '@/components/ui/Field';
import { SourceLink } from '@/components/ui/SourceLink';
import { EconomicChart } from './EconomicChart';
import { currencyAnalysis, FX_CODES, type FxCode } from './currencyCalculations';
import { formatEconomicValue } from './economyPresentation';

export function CurrencyAnalysis({ items }: { items: readonly EconomySeries[] }) {
  const [base, setBase] = useState<FxCode>('GBP');
  const [quote, setQuote] = useState<FxCode>('USD');
  const [days, setDays] = useState(90);
  const data = currencyAnalysis(items, base, quote, days);
  const options = FX_CODES.map((value) => ({ value, label: value }));
  return (
    <section
      aria-label="Currency movement analysis"
      className="space-y-6 border-t border-line pt-7"
    >
      <header className="flex flex-wrap items-end justify-between gap-5">
        <div>
          <h2 className="text-xl font-semibold">Currency movement analysis</h2>
          <p className="mt-2 text-sm text-muted">
            Explore how one currency changed against another over the available daily reference
            history.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <SelectField
            label="Base currency"
            value={base}
            onChange={(e) => setBase(e.target.value as FxCode)}
            options={options}
          />
          <SelectField
            label="Quote currency"
            value={quote}
            onChange={(e) => setQuote(e.target.value as FxCode)}
            options={options}
          />
          <SelectField
            label="Currency analysis period"
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            options={[
              { value: '30', label: '30 days' },
              { value: '90', label: '90 days' },
            ]}
          />
        </div>
      </header>
      {!data ? (
        <p className="py-8 text-sm text-muted">
          {base === quote
            ? 'Choose two different currencies to compare their movement.'
            : 'No matching published dates are available for this pair. Try another pair or refresh the data.'}
        </p>
      ) : (
        <>
          <div className="grid gap-8 xl:grid-cols-[minmax(0,1fr)_280px]">
            <EconomicChart key={`${base}:${quote}:${days}`} series={data.series} />
            <aside className="space-y-4 text-sm leading-6 text-muted">
              <h3 className="font-semibold text-text">What changed</h3>
              <p>
                {data.change === null ? (
                  'Only one matching observation is available, so a period change cannot be calculated.'
                ) : (
                  <>
                    {base}{' '}
                    {Math.abs(data.change) < 0.000001
                      ? 'was unchanged'
                      : data.change > 0
                        ? 'strengthened'
                        : 'weakened'}{' '}
                    against {quote} by{' '}
                    <strong className="font-mono text-text">
                      {Math.abs(data.change).toFixed(2)}%
                    </strong>{' '}
                    between {data.first.date} and {data.last.date}.
                  </>
                )}
              </p>
              <p>
                A higher line means one {base} buys more {quote}. It does not measure purchasing
                power against domestic goods.
              </p>
              <dl className="grid grid-cols-2 gap-3 text-xs">
                <div>
                  <dt>Observed low</dt>
                  <dd className="font-mono text-text">
                    {formatEconomicValue(data.low, data.series.unit)}
                  </dd>
                </div>
                <div>
                  <dt>Observed high</dt>
                  <dd className="font-mono text-text">
                    {formatEconomicValue(data.high, data.series.unit)}
                  </dd>
                </div>
                <div>
                  <dt>Matching dates</dt>
                  <dd className="font-mono text-text">{data.count}</dd>
                </div>
                <div>
                  <dt>Latest reference</dt>
                  <dd className="font-mono text-text">
                    {data.last.date}
                    {data.series.status === 'stale' ? ' · cached' : ''}
                  </dd>
                </div>
              </dl>
              <p className="text-xs">
                The window ends at the latest matching observation. These are observed daily
                extremes, not intraday highs/lows or a forecast.
              </p>
              <SourceLink url={data.series.source_url}>ECB source data</SourceLink>
            </aside>
          </div>
          <details className="text-xs leading-5 text-muted">
            <summary className="w-fit cursor-pointer py-2 hover:text-text">
              Calculation method
            </summary>
            <p>
              {data.series.note} Dates without both rates remain gaps. Relative change is (last rate
              ÷ first rate − 1) × 100. No transaction costs or spreads are included.
            </p>
          </details>
        </>
      )}
    </section>
  );
}

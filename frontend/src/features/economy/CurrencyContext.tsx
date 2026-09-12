import { useState } from 'react';
import { SourceLink } from '@/components/ui/SourceLink';
import type { EconomySeries } from '@/lib/api/economy';
import { EconomicChart } from './EconomicChart';
import { latestObservation } from './economyPresentation';

export function CurrencyContext({ items }: { items: readonly EconomySeries[] }) {
  const [choice, setChoice] = useState<string | null>(null);
  const available = items.filter((item) => item.points.some((point) => point.value !== null));
  const selected = available.find((item) => item.id === choice) ?? available[0];
  return (
    <section aria-label="Currency reference rates" className="space-y-5 border-t border-line pt-7">
      <header>
        <h2 className="text-lg font-semibold">Currency context</h2>
        <p className="mt-2 text-sm text-muted">
          Daily ECB reference rates, units of currency per €1. These are not live trading quotes.
        </p>
      </header>
      <div className="grid gap-8 lg:grid-cols-[240px_minmax(0,1fr)]">
        <div className="space-y-1">
          {items.map((item) => {
            const latest = latestObservation(item);
            return (
              <button
                key={item.id}
                type="button"
                disabled={!latest}
                aria-pressed={selected?.id === item.id}
                onClick={() => setChoice(item.id)}
                className={`flex w-full items-start justify-between gap-4 rounded-md px-3 py-3 text-left text-sm transition-colors disabled:cursor-default ${selected?.id === item.id ? 'bg-surface-2 text-ember' : 'text-muted enabled:hover:bg-surface-2'}`}
              >
                <span>
                  {item.name}
                  <span className="mt-1 block text-[10px] text-muted">
                    {latest?.date ?? 'Not published by this provider'}
                  </span>
                </span>
                <span className="font-mono">{latest?.value?.toFixed(4) ?? '—'}</span>
              </button>
            );
          })}
          <p className="pt-3 text-xs leading-5 text-muted">
            The ECB has suspended RUB reference rates. It does not publish an IRR reference rate.
            Neither is inferred from another currency.
          </p>
        </div>
        {selected ? (
          <div>
            <EconomicChart key={selected.id} series={selected} />
            <p className="mt-2 text-xs leading-5 text-muted">
              {selected.note} <SourceLink url={selected.source_url}>ECB source</SourceLink>
            </p>
          </div>
        ) : (
          <p className="self-center text-sm text-muted">
            Currency history is currently unavailable. Try refreshing the indicators.
          </p>
        )}
      </div>
    </section>
  );
}

import { useState } from 'react';

import { SIDE_LABELS, type Side, type UkraineReference } from '@/lib/api/ukraine';

import type { ChartLayout } from './ForceChart';
import { ForceSidePanel } from './ForceSidePanel';
import { useChartLayout } from './useChartLayout';

type View = Side | 'both';

const VIEWS: readonly (readonly [View, string])[] = [
  ['ru', SIDE_LABELS.ru],
  ['ua', SIDE_LABELS.ua],
  ['both', 'Compare both'],
];

const LAYOUTS: readonly (readonly [ChartLayout, string])[] = [
  ['chart', 'Chart'],
  ['stacked', 'Outline'],
];

function Toggle<T extends string>({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: readonly (readonly [T, string])[];
  value: T;
  onChange: (next: T) => void;
}) {
  return (
    <div role="group" aria-label={label} className="flex flex-wrap gap-1">
      {options.map(([key, text]) => (
        <button
          key={key}
          type="button"
          aria-pressed={value === key}
          onClick={() => onChange(key)}
          className="min-h-10 rounded border border-line px-3 text-xs text-muted aria-pressed:border-cyan aria-pressed:bg-cyan/10 aria-pressed:text-cyan"
        >
          {text}
        </button>
      ))}
    </div>
  );
}

/**
 * Organisation charts for both sides. Each chart is a nested list drawn with connector lines,
 * collapsible branch by branch, with a detail panel for the entry the reader focuses.
 */
export function ForcesSection({
  reference,
  fetcher,
}: {
  reference: UkraineReference;
  fetcher?: ((path: string) => Promise<Blob>) | undefined;
}) {
  const [view, setView] = useState<View>('both');
  const [override, setOverride] = useState<ChartLayout | null>(null);
  const layout = useChartLayout(override);
  const sides: readonly Side[] = view === 'both' ? ['ru', 'ua'] : [view];
  return (
    <section id="forces" aria-labelledby="ukraine-forces-heading" className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 id="ukraine-forces-heading" className="text-base font-semibold">
          Force organisation
        </h2>
        <div className="flex flex-wrap gap-2">
          <Toggle label="Side" options={VIEWS} value={view} onChange={setView} />
          <Toggle label="Layout" options={LAYOUTS} value={layout} onChange={setOverride} />
        </div>
      </div>
      <p className="max-w-3xl text-xs text-muted">
        Reported public structure, not an order of battle from observation. Commanders and strengths
        are as public reporting stated them on the date shown against each box, and those dates
        differ: an entry marked as possibly out of date has not been reviewed within a year of the
        catalogue being built. Command arrangements change often and quietly, so treat the shape as
        indicative. Portraits and emblems are Wikimedia Commons files; the licence and credit appear
        in the detail panel when you open an entry.
      </p>
      <div className={view === 'both' ? 'grid gap-6 lg:grid-cols-2' : 'flex flex-col'}>
        {sides.map((side) => (
          <ForceSidePanel
            key={side}
            side={side}
            reference={reference}
            layout={layout}
            fetcher={fetcher}
          />
        ))}
      </div>
    </section>
  );
}

import { ECONOMY_PERIODS, type EconomyDays } from '@/lib/api/economyBriefing';

export function EconomyPeriodPicker({
  days,
  onChange,
}: {
  days: EconomyDays;
  onChange: (days: EconomyDays) => void;
}) {
  return (
    <section
      aria-label="Economic summary period"
      className="flex flex-wrap items-center justify-between gap-4 border-y border-line py-4"
    >
      <div>
        <h2 className="text-sm font-semibold">Summary period</h2>
        <p className="mt-1 max-w-2xl text-xs leading-5 text-muted">
          Choose how far back the news and research summary should look. Annual indicators keep
          their own observation dates.
        </p>
      </div>
      <div
        role="group"
        aria-label="Choose summary period"
        className="flex gap-1 rounded-lg bg-surface p-1"
      >
        {ECONOMY_PERIODS.map((period) => (
          <button
            key={period}
            type="button"
            aria-pressed={days === period}
            onClick={() => onChange(period)}
            className={`min-h-11 min-w-16 rounded-md px-3 text-sm transition-colors ${days === period ? 'bg-ember text-ground font-semibold' : 'text-muted hover:bg-surface-2 hover:text-text'}`}
          >
            {period} Day
          </button>
        ))}
      </div>
    </section>
  );
}

import { Sparkline } from '@/components/charts/Sparkline';
import { formatCount } from '@/components/charts/chartSlots';
import type { CyberSnapshot } from '@/lib/api/cyber';
import { kpis } from './cyberModel';

/** Stat tiles: the headline numbers with their daily shape beside them. */
export function CyberKpis({ data }: { data: CyberSnapshot }) {
  return (
    <ul
      aria-label="Cyber reporting headline figures"
      className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6"
    >
      {kpis(data).map((kpi) => (
        <li
          key={kpi.key}
          className="rounded-xl border border-line/70 bg-surface/60 p-4 transition-colors hover:border-line"
        >
          <p className="text-[11px] text-muted">{kpi.label}</p>
          <p className="mt-1 text-2xl font-semibold tracking-tight">{formatCount(kpi.value)}</p>
          <p className="mt-0.5 truncate text-[11px] text-muted">{kpi.caption}</p>
          <div className="mt-3">
            <Sparkline
              values={kpi.series}
              slot={kpi.slot}
              label={`${kpi.label} per day: ${kpi.series.join(', ')}`}
            />
          </div>
        </li>
      ))}
    </ul>
  );
}

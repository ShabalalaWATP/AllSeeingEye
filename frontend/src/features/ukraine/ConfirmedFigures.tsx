import { ShareBar } from '@/components/charts/ShareBar';
import { Sparkline } from '@/components/charts/Sparkline';
import { BasisBadge } from '@/components/ui/BasisBadge';
import { SIDE_LABELS, type CivilianHarm, type ConfirmedLosses, type Side } from '@/lib/api/ukraine';

const SIDES: readonly Side[] = ['ru', 'ua'];

/** Oryx totals per side as a part-to-whole bar, with a month of daily totals beneath. */
export function OryxCards({ confirmed }: { confirmed: ConfirmedLosses }) {
  return (
    <>
      {SIDES.map((side) => {
        const total = confirmed.rows.find(
          (row) => row.side === side && row.equipment_type === 'All Types',
        );
        if (!total) return null;
        const days = confirmed.days.filter((day) => day.side === side).map((day) => day.total);
        return (
          <li
            key={side}
            className="flex flex-col gap-1 rounded-card border border-line bg-surface p-3"
          >
            <div className="flex items-center justify-between gap-2">
              <span className="font-mono text-[11px] uppercase tracking-wide text-muted">
                {SIDE_LABELS[side]} losses, Oryx
              </span>
              <BasisBadge basis="visually_confirmed" />
            </div>
            <span className="text-xl font-semibold tabular-nums">
              {total.total.toLocaleString('en-GB')}
            </span>
            <ShareBar
              label={`${SIDE_LABELS[side]} confirmed losses by status`}
              parts={[
                { key: 'destroyed', label: 'Destroyed', value: total.destroyed, slot: 2 },
                { key: 'damaged', label: 'Damaged', value: total.damaged, slot: 4 },
                { key: 'abandoned', label: 'Abandoned', value: total.abandoned, slot: 5 },
                { key: 'captured', label: 'Captured', value: total.captured, slot: 3 },
              ]}
            />
            <span className="text-xs text-muted">
              recorded {confirmed.recorded_on}, photographed losses only
            </span>
            {days.length > 1 ? (
              <Sparkline
                values={days}
                slot={side === 'ru' ? 2 : 1}
                label={`${SIDE_LABELS[side]} cumulative confirmed losses, last month`}
              />
            ) : null}
          </li>
        );
      })}
    </>
  );
}

/** The latest HRMMU month with figures, badged as documented. */
export function HarmCard({ harm }: { harm: CivilianHarm }) {
  const latest = harm.months.find((month) => month.killed !== null);
  if (!latest) return null;
  const label = new Date(`${latest.month}T00:00:00Z`).toLocaleDateString('en-GB', {
    month: 'long',
    year: 'numeric',
    timeZone: 'UTC',
  });
  return (
    <li className="flex flex-col gap-1 rounded-card border border-line bg-surface p-3">
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-[11px] uppercase tracking-wide text-muted">
          Civilians killed, {label}
        </span>
        <BasisBadge basis="documented" />
      </div>
      <span className="text-xl font-semibold tabular-nums">
        {(latest.killed ?? 0).toLocaleString('en-GB')}
      </span>
      <span className="text-xs text-muted">
        {(latest.injured ?? 0).toLocaleString('en-GB')} injured, verified by the UN monitoring
        mission
      </span>
      <a
        href={latest.url}
        target="_blank"
        rel="noopener noreferrer"
        className="text-xs text-ember hover:underline"
      >
        Monthly update
      </a>
    </li>
  );
}

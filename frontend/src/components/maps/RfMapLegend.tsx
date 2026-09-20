import { RF_STATUS_CSS } from '@/lib/map/rfTerrainPresentation';
import type { RfTerrainStatus } from '@/lib/map/rfTerrainTypes';

export function RfMapLegend({ terrain = true }: { terrain?: boolean }) {
  const entries: { status: RfTerrainStatus; symbol: string; label: string }[] = terrain
    ? [
        { status: 'clear', symbol: '━', label: 'Clear at checked points' },
        { status: 'risk', symbol: '△', label: 'Clearance or weak-signal risk' },
        { status: 'blocked', symbol: '×', label: 'Direct path obstructed' },
        { status: 'unknown', symbol: '···', label: 'Not assessed' },
      ]
    : [
        { status: 'clear', symbol: '━', label: 'Within ideal limit' },
        { status: 'blocked', symbol: '×', label: 'Beyond ideal limit' },
      ];
  return (
    <div aria-label="RF map legend" className="grid grid-cols-2 gap-x-3 gap-y-2 text-[10px]">
      {entries.map(({ status, symbol, label }) => (
        <div key={status} className="flex items-center gap-2">
          <span
            aria-hidden="true"
            className="w-4 text-center text-base font-bold"
            style={{ color: RF_STATUS_CSS[status] }}
          >
            {symbol}
          </span>
          <span>{label}</span>
        </div>
      ))}
    </div>
  );
}

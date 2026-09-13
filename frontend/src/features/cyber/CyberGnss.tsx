import { BarList } from '@/components/charts/BarList';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SourceLink } from '@/components/ui/SourceLink';
import type { JamMap } from '@/lib/api/aviation';
import { describeError, type ApiError } from '@/lib/api/errors';
import type { CyberItem } from '@/lib/api/cyber';
import { formatUtc } from '@/lib/format';
import { ChartCard } from './CyberCharts';
import { formatCellPosition, summariseJamCells } from './gnssRegions';

export interface CyberGnssSnapshot {
  data: JamMap | null;
  loading: boolean;
  error: ApiError | null;
  reload: () => Promise<void>;
}

function Figure({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-line/60 bg-ground/40 px-3 py-2">
      <p className="text-[11px] text-muted">{label}</p>
      <p className="mt-0.5 text-lg font-semibold tracking-tight">{value}</p>
    </div>
  );
}

/** Aircraft-accuracy interference cells by region, beside reporting that mentions jamming. */
export function CyberGnss({
  gnss,
  items,
  onOpenMap,
}: {
  gnss: CyberGnssSnapshot;
  items: readonly CyberItem[];
  onOpenMap: () => void;
}) {
  const summary = gnss.data ? summariseJamCells(gnss.data.cells) : null;
  return (
    <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
      <ChartCard
        title="Aircraft accuracy anomalies by region"
        note="Approximately the last 24 hours"
      >
        {gnss.loading && !gnss.data && (
          <p role="status" className="text-xs text-muted">
            Loading the interference snapshot…
          </p>
        )}
        {gnss.error && (
          <Alert tone="error">
            {describeError(gnss.error)}{' '}
            <Button variant="ghost" onClick={() => void gnss.reload()}>
              Retry interference snapshot
            </Button>
          </Alert>
        )}
        {summary && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              <Figure label="Flagged cells" value={summary.total.toLocaleString('en-GB')} />
              <Figure label="Red (above 10%)" value={summary.red.toLocaleString('en-GB')} />
              <Figure label="Amber (2% to 10%)" value={summary.amber.toLocaleString('en-GB')} />
              <Figure label="Observations" value={summary.observations.toLocaleString('en-GB')} />
            </div>
            <BarList
              rows={summary.regions.map((region) => ({
                key: region.key,
                label: region.label,
                value: region.cells,
                note: region.red ? `${region.red} red` : undefined,
              }))}
              label="Flagged one-degree cells per region"
              slot={6}
              emptyText="No amber or red cells in the current snapshot. Receiver coverage varies; a blank region is not evidence of no interference."
            />
            {summary.worst.length > 0 && (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <caption className="sr-only">
                    Cells with the highest share of degraded reports
                  </caption>
                  <thead className="text-muted">
                    <tr>
                      <th className="py-1 pr-3 font-medium">Cell centre</th>
                      <th className="px-2 py-1 font-medium">Degraded share</th>
                      <th className="px-2 py-1 font-medium">Reports</th>
                      <th className="px-2 py-1 font-medium">Level</th>
                    </tr>
                  </thead>
                  <tbody>
                    {summary.worst.map((cell) => (
                      <tr key={`${cell.lon}:${cell.lat}`} className="border-t border-line/60">
                        <td className="py-1 pr-3 font-mono tabular-nums">
                          {formatCellPosition(cell)}
                        </td>
                        <td className="px-2 py-1 font-mono tabular-nums">
                          {cell.percent_bad.toFixed(1)}%
                        </td>
                        <td className="px-2 py-1 font-mono tabular-nums">{cell.good + cell.bad}</td>
                        <td className="px-2 py-1">
                          <span
                            className={`inline-flex items-center gap-1.5 ${cell.level === 'red' ? 'text-critical' : 'text-amber'}`}
                          >
                            <span aria-hidden="true" className="size-1.5 rounded-full bg-current" />
                            {cell.level}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <p className="text-[11px] leading-5 text-muted">
              Latest aircraft observation{' '}
              {gnss.data?.updated_at ? formatUtc(gnss.data.updated_at) : 'not available'}. Cells bin
              ADS-B navigation-accuracy reports into one-degree squares. They cannot confirm
              deliberate jamming or spoofing, identify a constellation or locate a transmitter.
            </p>
            <Button variant="secondary" onClick={onOpenMap}>
              Show GNSS cells on the map
            </Button>
          </div>
        )}
      </ChartCard>
      <ChartCard title="Reporting that mentions navigation interference" note="Selected period">
        {items.length ? (
          <ul className="space-y-3">
            {items.slice(0, 8).map((item) => (
              <li key={item.id} className="text-xs leading-5">
                <SourceLink url={item.url}>{item.title}</SourceLink>
                <p className="text-muted">
                  {item.source_name} · {formatUtc(item.published_at)}
                </p>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-xs leading-5 text-muted">
            No returned record mentions GPS or GNSS jamming or spoofing in this period. Publisher
            feeds are headline-only, so quieter reporting can be missed.
          </p>
        )}
      </ChartCard>
    </div>
  );
}

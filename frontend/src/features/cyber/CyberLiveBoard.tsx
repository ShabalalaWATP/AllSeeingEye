import { BarList } from '@/components/charts/BarList';
import { formatCount } from '@/components/charts/chartSlots';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { describeError } from '@/lib/api/errors';

import { ChartCard } from './CyberCharts';
import { liveTallyRows } from './cyberPresentation';
import type { CyberLiveState } from './useCyberWorkspace';

function Figure({ label, value }: { label: string; value: number }) {
  return (
    <li className="rounded-xl border border-line/70 bg-surface/60 p-4">
      <p className="text-[11px] text-muted">{label}</p>
      <p className="mt-1 text-2xl font-semibold tracking-tight">{formatCount(value)}</p>
    </li>
  );
}

/** The fixed-window outage and ransomware tallies that were the old tracker board. */
export function CyberLiveBoard({ state }: { state: CyberLiveState }) {
  const { data, loading, error } = state;
  if (error)
    return (
      <Alert tone="error">
        {describeError(error)}{' '}
        <Button variant="ghost" onClick={() => void state.reload()}>
          Retry live board
        </Button>
      </Alert>
    );
  if (!data) return loading ? <LoadingNote label="Loading the live cyber board" /> : null;
  return (
    <div className="space-y-4">
      <ul aria-label="Live cyber figures" className="grid gap-3 sm:grid-cols-2">
        <Figure label="Outage alerts, last 24 hours" value={data.outages_24h} />
        <Figure label="Ransomware claims, last 7 days" value={data.ransomware_7d} />
      </ul>
      <div className="grid gap-4 lg:grid-cols-3">
        <ChartCard title="Outages by nation" note="Last 24 hours">
          <BarList
            rows={liveTallyRows(data.outages_by_country, true)}
            label="Outage alerts by nation"
            slot={3}
            emptyText="No outage alerts in the last 24 hours."
          />
        </ChartCard>
        <ChartCard title="Ransomware claims by group" note="Last 7 days">
          <BarList
            rows={liveTallyRows(data.ransomware_by_group, false)}
            label="Ransomware claims by group"
            slot={5}
            emptyText="No ransomware claims in the last 7 days."
          />
        </ChartCard>
        <ChartCard title="Ransomware claims by nation" note="Victim location as claimed">
          <BarList
            rows={liveTallyRows(data.ransomware_by_country, true)}
            label="Ransomware claims by nation"
            slot={5}
            emptyText="No ransomware claims in the last 7 days."
          />
        </ChartCard>
      </div>
    </div>
  );
}

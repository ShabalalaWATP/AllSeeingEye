import type { ReactNode } from 'react';
import { BarList } from '@/components/charts/BarList';
import { ShareBar } from '@/components/charts/ShareBar';
import { StackedColumns } from '@/components/charts/StackedColumns';
import type { CyberSnapshot } from '@/lib/api/cyber';
import {
  countryRows,
  kindSeries,
  kindShares,
  natoCountryRows,
  sourceRows,
  timelineDays,
} from './cyberModel';
import { RadarAttackTrends } from './RadarAttackTrends';

export function ChartCard({
  title,
  note,
  children,
  className = '',
}: {
  title: string;
  note?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section
      aria-label={title}
      className={`rounded-xl border border-line/70 bg-surface/60 p-4 sm:p-5 ${className}`}
    >
      <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-sm font-semibold">{title}</h3>
        {note && <span className="font-mono text-[10px] text-muted">{note}</span>}
      </div>
      {children}
    </section>
  );
}

export function CyberCharts({
  data,
  onCountry,
}: {
  data: CyberSnapshot;
  onCountry: (country: string) => void;
}) {
  return (
    <div className="space-y-5">
      <div className="grid gap-4 lg:grid-cols-3">
        <ChartCard
          title="Reporting activity"
          note="UTC · records per calendar day"
          className="lg:col-span-2"
        >
          <StackedColumns
            days={timelineDays(data)}
            series={kindSeries(data)}
            label="Daily cyber reporting volume"
          />
          <p className="mt-3 text-xs leading-5 text-muted">
            Volume measures source output, not attack severity. The first and last days can be
            partial; one outage may produce several sensor records.
          </p>
        </ChartCard>
        <ChartCard
          title="Share by record kind"
          note={`${data.retained_count.toLocaleString()} dated`}
        >
          <ShareBar parts={kindShares(data)} label="Share of records by kind" />
        </ChartCard>
        <ChartCard title="Countries in the evidence" note="Source context, not origins">
          <BarList
            rows={countryRows(data)}
            label="Records by source-supplied country"
            slot={2}
            onSelect={onCountry}
            emptyText="Locations are not established for these records."
          />
        </ChartCard>
        <ChartCard title="NATO member context" note="Members with attributed records">
          <BarList
            rows={natoCountryRows(data)}
            label="Records with country context in NATO member states"
            slot={1}
            onSelect={onCountry}
            emptyText="No records carry country context inside the alliance in this period."
          />
          <p className="mt-3 text-xs leading-5 text-muted">
            Victim or outage country as reported by the source. Membership is not a statement about
            who is responsible.
          </p>
        </ChartCard>
        <ChartCard title="Source output" note="Retained records">
          <BarList
            rows={sourceRows(data)}
            label="Records per source"
            slot={3}
            emptyText="No source returned dated records in this period."
          />
        </ChartCard>
      </div>
      <section aria-label="Cloudflare Radar observed attack traffic" className="space-y-3">
        <div>
          <h3 className="text-sm font-semibold">Cloudflare Radar · observed attack traffic</h3>
          <p className="mt-1 text-xs leading-5 text-muted">
            A separate provider-wide view of mitigated network and application traffic. These
            percentages use the latest one-day Radar window, independently of the selected report
            period, and are excluded from the incident and reporting counts above.
          </p>
        </div>
        <RadarAttackTrends />
      </section>
    </div>
  );
}

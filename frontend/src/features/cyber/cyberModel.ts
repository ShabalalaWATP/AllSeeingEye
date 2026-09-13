/** Pure reading models over a cyber snapshot. Counts describe collected reporting only. */
import type { ChartSlot } from '@/components/charts/chartSlots';
import type { ColumnSeries } from '@/components/charts/StackedColumns';
import type { BarRow } from '@/components/charts/BarList';
import type { SharePart } from '@/components/charts/ShareBar';
import type { CyberActor, CyberItem, CyberSnapshot, CyberTheme } from '@/lib/api/cyber';
import { CYBER_KIND_LABELS, type CyberKind } from '@/lib/cyber';
import { CYBER_THEME_META, NATO_MEMBER_ISO } from '@/lib/cyberThemes';
import { cyberCountry } from './cyberPresentation';

/** Colour follows the record kind, in every chart, whatever is filtered out. */
export const KIND_SLOT: Record<CyberKind, ChartSlot> = {
  advisory: 1,
  ransomware_claim: 2,
  threat_report: 3,
  outage_signal: 4,
  known_exploited_vulnerability: 5,
  news_report: 6,
  other: 'muted',
};

export const THEME_SLOT: Record<CyberTheme, ChartSlot> = {
  nation_state: 5,
  nato_allies: 1,
  uk_infrastructure: 2,
  ukraine: 4,
  gnss_interference: 6,
  critical_infrastructure: 3,
};

const KIND_ORDER: readonly CyberKind[] = [
  'advisory',
  'threat_report',
  'news_report',
  'ransomware_claim',
  'known_exploited_vulnerability',
  'outage_signal',
  'other',
];

export function countOf(snapshot: CyberSnapshot, kind: CyberKind): number {
  return snapshot.counts.find((row) => row.kind === kind)?.count ?? 0;
}

export function timelineDays(snapshot: CyberSnapshot): string[] {
  return snapshot.timeline.map((day) => day.day);
}

export function dailyTotals(snapshot: CyberSnapshot): number[] {
  return snapshot.timeline.map((day) => day.total);
}

export function dailyKind(snapshot: CyberSnapshot, kind: CyberKind): number[] {
  return snapshot.timeline.map((day) => day.counts.find((row) => row.kind === kind)?.count ?? 0);
}

/** Kinds with at least one record, in a fixed order so the stack never re-sorts. */
export function kindSeries(snapshot: CyberSnapshot): ColumnSeries[] {
  return KIND_ORDER.filter((kind) => countOf(snapshot, kind) > 0).map((kind) => ({
    key: kind,
    label: CYBER_KIND_LABELS[kind],
    slot: KIND_SLOT[kind],
    values: dailyKind(snapshot, kind),
  }));
}

export function kindShares(snapshot: CyberSnapshot): SharePart[] {
  return KIND_ORDER.map((kind) => ({
    key: kind,
    label: CYBER_KIND_LABELS[kind],
    value: countOf(snapshot, kind),
    slot: KIND_SLOT[kind],
  }));
}

export function sourceRows(snapshot: CyberSnapshot, limit = 8): BarRow[] {
  return [...snapshot.sources]
    .filter((source) => source.retained_count > 0)
    .sort((a, b) => b.retained_count - a.retained_count || a.name.localeCompare(b.name))
    .slice(0, limit)
    .map((source) => ({
      key: source.source_id,
      label: source.name,
      value: source.retained_count,
      note: source.status === 'degraded' ? 'degraded' : undefined,
    }));
}

export function countryRows(snapshot: CyberSnapshot, limit = 8): BarRow[] {
  return snapshot.top_countries.slice(0, limit).map((row) => ({
    key: row.key,
    label: cyberCountry(row.key),
    value: row.count,
    note: NATO_MEMBER_ISO.has(row.key) ? 'NATO member' : undefined,
  }));
}

/** Source-attributed country context inside the alliance, not attacker origins. */
export function natoCountryRows(snapshot: CyberSnapshot, limit = 8): BarRow[] {
  return snapshot.top_countries
    .filter((row) => NATO_MEMBER_ISO.has(row.key))
    .slice(0, limit)
    .map((row) => ({ key: row.key, label: cyberCountry(row.key), value: row.count }));
}

export interface ThemeView {
  theme: CyberTheme;
  label: string;
  short: string;
  detail: string;
  count: number;
  daily: number[];
  slot: ChartSlot;
  items: CyberItem[];
}

export function themeViews(snapshot: CyberSnapshot, perTheme = 3): ThemeView[] {
  return snapshot.themes.map((tally) => {
    const meta = CYBER_THEME_META[tally.theme];
    return {
      theme: tally.theme,
      label: meta.label,
      short: meta.short,
      detail: meta.detail,
      count: tally.count,
      daily: [...tally.daily],
      slot: THEME_SLOT[tally.theme],
      items: snapshot.items.filter((item) => item.themes.includes(tally.theme)).slice(0, perTheme),
    };
  });
}

export interface StateRow extends BarRow {
  actors: string[];
}

/** Records mentioning actors whose reference profile names a state; the state is MITRE wording. */
export function stateRows(snapshot: CyberSnapshot, actors: readonly CyberActor[]): StateRow[] {
  const names = new Map(actors.map((actor) => [actor.group_id, actor.name]));
  return snapshot.state_mentions.map((row) => ({
    key: row.state,
    label: row.state,
    value: row.count,
    actors: row.group_ids.map((id) => names.get(id) ?? id),
  }));
}

/** Actors mentioned in the period, with their profile's state association when recorded. */
export function mentionedActors(snapshot: CyberSnapshot, actors: readonly CyberActor[], limit = 8) {
  const byId = new Map(actors.map((actor) => [actor.group_id, actor]));
  return snapshot.actor_mentions.slice(0, limit).map((mention) => ({
    group_id: mention.group_id,
    name: mention.name,
    count: mention.count,
    state: byId.get(mention.group_id)?.state_association ?? null,
  }));
}

export interface Kpi {
  key: string;
  label: string;
  value: number;
  caption: string;
  series: number[];
  slot: ChartSlot;
}

export function kpis(snapshot: CyberSnapshot): Kpi[] {
  const stateLinked = snapshot.themes.find((row) => row.theme === 'nation_state');
  return [
    {
      key: 'total',
      label: 'Dated records',
      value: snapshot.retained_count,
      caption: 'All enabled feeds',
      series: dailyTotals(snapshot),
      slot: 1,
    },
    {
      key: 'ransomware',
      label: 'Ransomware claims',
      value: countOf(snapshot, 'ransomware_claim'),
      caption: 'Unverified criminal claims',
      series: dailyKind(snapshot, 'ransomware_claim'),
      slot: KIND_SLOT.ransomware_claim,
    },
    {
      key: 'kev',
      label: 'KEV additions',
      value: countOf(snapshot, 'known_exploited_vulnerability'),
      caption: 'CISA catalogue additions',
      series: dailyKind(snapshot, 'known_exploited_vulnerability'),
      slot: KIND_SLOT.known_exploited_vulnerability,
    },
    {
      key: 'publications',
      label: 'Advisories and research',
      value:
        countOf(snapshot, 'advisory') +
        countOf(snapshot, 'threat_report') +
        countOf(snapshot, 'news_report'),
      caption: 'Official, vendor and press headlines',
      series: snapshot.timeline.map(
        (day) =>
          (day.counts.find((row) => row.kind === 'advisory')?.count ?? 0) +
          (day.counts.find((row) => row.kind === 'threat_report')?.count ?? 0) +
          (day.counts.find((row) => row.kind === 'news_report')?.count ?? 0),
      ),
      slot: KIND_SLOT.advisory,
    },
    {
      key: 'outages',
      label: 'Connectivity signals',
      value: countOf(snapshot, 'outage_signal'),
      caption: 'Measurements, not attacks',
      series: dailyKind(snapshot, 'outage_signal'),
      slot: KIND_SLOT.outage_signal,
    },
    {
      key: 'nation_state',
      label: 'Nation-state lens',
      value: stateLinked?.count ?? 0,
      caption: 'Text or profile matches',
      series: [...(stateLinked?.daily ?? [])],
      slot: THEME_SLOT.nation_state,
    },
  ];
}

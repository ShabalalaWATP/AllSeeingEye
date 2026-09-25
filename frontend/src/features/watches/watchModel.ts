/**
 * What each kind of standing watch is, and how a list from its own API becomes a short
 * summary for the hub: a count and the few most recently changed items with links.
 */
import { annotationMonitorHref } from '@/lib/annotationMonitorLinks';
import type { AnnotationMonitor } from '@/lib/api/annotationMonitors';
import type { CollectionPlan } from '@/lib/api/direction';
import type { BriefSummary } from '@/lib/api/researchBriefSchema';
import type { Schedule } from '@/lib/api/schedules';
import type { Indicator } from '@/lib/api/warning';
import { formatInterval, formatUtc } from '@/lib/format';

export type WatchKind =
  'subscriptions' | 'alertRules' | 'areaWatches' | 'plans' | 'briefs' | 'monitors';

export interface WatchGroupInfo {
  readonly kind: WatchKind;
  readonly title: string;
  readonly explanation: string;
  readonly href: string;
  readonly linkLabel: string;
  readonly emptyText: string;
}

export interface WatchItem {
  readonly id: string;
  readonly label: string;
  readonly detail: string;
  readonly to: string;
}

export interface WatchSummary {
  readonly count: number;
  /** True when the list endpoint returned a full page, so more exist than were counted. */
  readonly more: boolean;
  readonly items: readonly WatchItem[];
}

/** Names the personal space or the team a record belongs to. */
export type WorkspaceLabel = (teamId: string | null | undefined) => string;

export const RECENT_LIMIT = 3;

export const WATCH_GROUPS: readonly WatchGroupInfo[] = [
  {
    kind: 'subscriptions',
    title: 'Subscriptions',
    explanation: 'Research that runs again on a schedule and saves each update as a report.',
    href: '/subscriptions',
    linkLabel: 'Open subscriptions',
    emptyText: 'No subscriptions yet.',
  },
  {
    kind: 'alertRules',
    title: 'Alert rules',
    explanation:
      'Rules that raise an alert when enough matching reports arrive in the live feeds within a time window.',
    href: '/warning',
    linkLabel: 'Open alerts',
    emptyText: 'No alert rules yet.',
  },
  {
    kind: 'areaWatches',
    title: 'Area watches',
    explanation: 'Alert rules for one area drawn on the map, raised by new activity inside it.',
    href: '/warning',
    linkLabel: 'Open alerts',
    emptyText: 'No area watches yet. Draw an area on the map and choose Watch this area.',
  },
  {
    kind: 'plans',
    title: 'Collection plans',
    explanation:
      'Intelligence requirements matched against the live feeds, gathering evidence as it arrives.',
    href: '/direction',
    linkLabel: 'Open plans and areas',
    emptyText: 'No collection plans yet.',
  },
  {
    kind: 'briefs',
    title: 'Research briefs',
    explanation:
      'Saved questions with their scope and sources, ready to run again or subscribe to.',
    href: '/research?brief=library',
    linkLabel: 'Open your briefs',
    emptyText: 'No saved briefs yet.',
  },
  {
    kind: 'monitors',
    title: 'Annotation monitors',
    explanation:
      'Checks on selected claims, identities or relationships in a saved report for later changes.',
    href: '/annotation-monitors',
    linkLabel: 'Open annotation monitors',
    emptyText: 'No annotation monitors yet.',
  },
];

function time(value: string): number {
  const parsed = Date.parse(value);
  return Number.isNaN(parsed) ? 0 : parsed;
}

/** Newest first by the given timestamp, cut to the few shown on the hub. */
export function mostRecent<T>(rows: readonly T[], at: (row: T) => string): T[] {
  return [...rows].sort((a, b) => time(at(b)) - time(at(a))).slice(0, RECENT_LIMIT);
}

function summary(items: readonly WatchItem[], count: number, more = false): WatchSummary {
  return { count, more, items };
}

export function summariseSubscriptions(
  rows: readonly Schedule[],
  label: WorkspaceLabel,
): WatchSummary {
  const items = mostRecent(rows, (row) => row.created_at).map((row) => ({
    id: row.id,
    label: row.name,
    detail: `${label(row.team_id)} · ${
      row.enabled ? `next run ${formatUtc(row.next_run_at)}` : 'paused'
    }`,
    to: '/subscriptions',
  }));
  return summary(items, rows.length);
}

/** An area watch is an alert rule bounded by a drawn box or an exact shape. */
export function isAreaWatch(indicator: Indicator): boolean {
  return indicator.bbox !== null || Boolean(indicator.research_area);
}

function ruleState(indicator: Indicator, active: string): string {
  return indicator.enabled ? active : 'switched off';
}

export function summariseAlertRules(
  rows: readonly Indicator[],
  label: WorkspaceLabel,
): WatchSummary {
  const rules = rows.filter((row) => !isAreaWatch(row));
  const items = mostRecent(rules, (row) => row.updated_at).map((row) => ({
    id: row.id,
    label: row.name,
    detail: `${label(row.team_id)} · ${ruleState(
      row,
      `${String(row.threshold)} or more in ${formatInterval(row.window_minutes * 60)}`,
    )}`,
    to: '/warning',
  }));
  return summary(items, rules.length);
}

export function summariseAreaWatches(
  rows: readonly Indicator[],
  label: WorkspaceLabel,
): WatchSummary {
  const areas = rows.filter(isAreaWatch);
  const items = mostRecent(areas, (row) => row.updated_at).map((row) => ({
    id: row.id,
    label: row.name,
    detail: `${label(row.team_id)} · ${ruleState(
      row,
      row.research_area ? 'exact shape' : 'map rectangle',
    )}`,
    to: '/warning',
  }));
  return summary(items, areas.length);
}

export function summarisePlans(
  rows: readonly CollectionPlan[],
  label: WorkspaceLabel,
): WatchSummary {
  const items = mostRecent(rows, (row) => row.updated_at).map((row) => {
    const sirs = row.pirs.reduce((total, pir) => total + pir.sirs.length, 0);
    return {
      id: row.id,
      label: row.name,
      detail: `${label(row.team_id)} · ${String(row.pirs.length)} PIR, ${String(sirs)} SIR`,
      to: `/direction/plans/${encodeURIComponent(row.id)}`,
    };
  });
  return summary(items, rows.length);
}

export function summariseBriefs(
  page: { items: readonly BriefSummary[]; limit: number },
  label: WorkspaceLabel,
): WatchSummary {
  const items = mostRecent(page.items, (row) => row.revised_at).map((row) => ({
    id: row.id,
    label: row.title,
    detail: `${label(row.team_id)} · revision ${String(row.revision)}`,
    to: `/research?brief=${encodeURIComponent(row.id)}&revision=${String(row.revision)}`,
  }));
  return summary(items, page.items.length, page.items.length >= page.limit);
}

export function summariseMonitors(
  page: { items: readonly AnnotationMonitor[]; total: number },
  label: WorkspaceLabel,
): WatchSummary {
  const items = mostRecent(page.items, (row) => row.updated_at).map((row) => ({
    id: row.id,
    label: row.name,
    detail: `${label(row.team_id)} · ${row.status}`,
    to: annotationMonitorHref(row.id),
  }));
  return summary(items, page.total);
}

/** "3", or "50+" when a full page came back and more may exist. */
export function countLabel(value: WatchSummary): string {
  return value.more ? `${String(value.count)}+` : String(value.count);
}

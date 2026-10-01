/** Bell summaries: scoped unacknowledged alerts and the account's bell preferences. */
import type { Bell, BellAlert, BellMention, BellPreferences } from '@/lib/api/bell';

import { alert } from './fixtures.warning';

export const bellAlert: BellAlert = {
  id: alert.id,
  title: alert.title,
  summary: alert.summary,
  fired_at: alert.fired_at,
  indicator_id: alert.indicator_id,
  report_id: null,
  annotation_monitor_id: null,
  team_id: null,
  team_name: null,
  can_acknowledge: true,
};

export const noPreferences: BellPreferences = { muted_kinds: [], muted_rules: [] };

export const bellMention: BellMention = {
  post_id: 'e1e1e1e1-e1e1-4e1e-8e1e-e1e1e1e1e1e1',
  thread_id: 'f1f1f1f1-f1f1-4f1f-8f1f-f1f1f1f1f1f1',
  team_id: '33333333-3333-4333-8333-333333333333',
  team_name: 'Desk',
  author_name: 'Lead',
  snippet: '@analyst can you check the <b>rail</b> yard?',
  created_at: '2026-09-05T12:00:00Z',
};
export const noMentions: Bell['mentions'] = { items: [], unread: 0, muted: false };

export function bellSummary(
  items: BellAlert[] = [bellAlert],
  overrides: Partial<Omit<Bell, 'alerts'>> & { total?: number; muted?: boolean } = {},
): Bell {
  const { total, muted, ...rest } = overrides;
  return {
    window_days: 7,
    alerts: { items, total: total ?? items.length, muted: muted ?? false },
    mentions: noMentions,
    preferences: noPreferences,
    ...rest,
  };
}

export function bellAlerts(count: number, extra: Partial<BellAlert> = {}): BellAlert[] {
  return Array.from({ length: count }, (_, index) => ({
    ...bellAlert,
    id: `${String(index + 1)}1111111-1111-4111-8111-111111111111`,
    title: `Alert ${String(index + 1)}`,
    ...extra,
  }));
}

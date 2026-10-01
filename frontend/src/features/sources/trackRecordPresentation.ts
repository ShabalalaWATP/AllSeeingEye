import type { SourceTrackRecord } from '@/lib/api/sourceTrackRecord';

const COUNT = new Intl.NumberFormat('en-GB');

export const formatCount = (value: number): string => COUNT.format(value);

export const plural = (count: number, one: string, many = `${one}s`): string =>
  `${formatCount(count)} ${count === 1 ? one : many}`;

export const STATUS_LABELS = {
  ready: 'Ready',
  needs_review: 'Needs review',
  failed: 'Failed',
} as const;

export const REVIEW_KIND_LABELS = {
  reliability: 'Reliability',
  credibility: 'Credibility',
  authenticity: 'Authenticity',
} as const;

/** The population sentence always names the visible count and the report bound. */
export function populationText(record: SourceTrackRecord): string {
  const scope =
    record.visible_reports > record.reports_considered
      ? `the latest ${formatCount(record.reports_considered)} of your ${formatCount(record.visible_reports)} visible reports`
      : `your ${plural(record.visible_reports, 'visible report')}`;
  if (record.reports_citing === 0) return `Not cited in ${scope}.`;
  return `Cited in ${plural(record.reports_citing, 'report')} (${plural(record.frozen_items, 'frozen item')}) from ${scope}.`;
}

export function boundText(record: SourceTrackRecord): string {
  return `At most the latest ${formatCount(record.report_bound)} visible reports are counted, each at its latest saved version. These are counts of frozen citations, not a measure of reliability.`;
}

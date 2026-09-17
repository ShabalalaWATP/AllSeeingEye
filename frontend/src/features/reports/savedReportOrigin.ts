/**
 * Where a saved report was asked for, so it is listed in the section that created it.
 *
 * New reports carry `origin` in their frozen scope. Reports saved before that keep the
 * same meaning by their focus: a photograph is a geolocation assessment, and anything
 * else is research the operator asked for directly.
 */
import type { ReportSummary } from '@/lib/api/reports';

export const SAVED_ORIGINS = ['research', 'subscription', 'geolocation'] as const;
export type SavedOrigin = (typeof SAVED_ORIGINS)[number];

function stated(scope: ReportSummary['scope']): SavedOrigin | null {
  const value = scope.origin;
  return SAVED_ORIGINS.find((origin) => origin === value) ?? null;
}

export function reportOrigin(report: ReportSummary): SavedOrigin {
  return (
    stated(report.scope) ?? (report.scope.research_focus === 'media' ? 'geolocation' : 'research')
  );
}

export function reportsFrom(
  reports: readonly ReportSummary[] | null,
  origin: SavedOrigin,
): readonly ReportSummary[] | null {
  return reports === null ? null : reports.filter((report) => reportOrigin(report) === origin);
}

const SAVED_PATHS: Record<SavedOrigin, string> = {
  research: '/research/saved',
  subscription: '/subscriptions/saved',
  geolocation: '/geolocation/saved',
};

/** The section that lists this report, for a reader returning from it. */
export function savedPathFor(report: ReportSummary | null | undefined): string {
  return report ? SAVED_PATHS[reportOrigin(report)] : SAVED_PATHS.research;
}

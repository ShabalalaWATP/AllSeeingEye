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

const SAVED_PATHS: Record<SavedOrigin, string> = {
  research: '/research/saved',
  subscription: '/subscriptions/saved',
  geolocation: '/geolocation/saved',
};

/** Automatic briefings are read in the workspace that prepared them, not Saved research. */
const BRIEFING_PATHS = new Map<unknown, string>([
  ['daily', '/trackers'],
  ['economy', '/economy'],
  ['cyber', '/cyber'],
]);

/** The section that lists this report, for a reader returning from it. */
export function savedPathFor(report: ReportSummary | null | undefined): string {
  if (report?.scope.origin === 'briefing')
    return BRIEFING_PATHS.get(report.scope.briefing) ?? '/research/jobs?briefings=1';
  return report ? SAVED_PATHS[reportOrigin(report)] : SAVED_PATHS.research;
}

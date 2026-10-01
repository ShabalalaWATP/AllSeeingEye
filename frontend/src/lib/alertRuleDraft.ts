/**
 * One pending "Watch for" hand-off from a report judgement to the alert rule form, in memory
 * only. Preparing it sends nothing: the rule exists only once the person chooses Add alert
 * rule. It is never written to a URL or browser storage, and it is discarded on sign-out,
 * account or role change and any workspace access change, like the area watch hand-off.
 *
 * Indicator wording is kept as plain text, whitespace-normalised and stripped of control
 * characters. Nothing is shortened: overlong or excessive phrases stay visible so the
 * person edits them before the rule can be saved.
 */
import { useSyncExternalStore } from 'react';

import { useAuthStore } from '@/stores/auth';

import { CATEGORIES } from './api/eventSchemas';

import { clearAreaWatchDraft, subscribeAreaWatchDraft } from './areaWatchDraft';
import { subscribeWorkspaceAccess, workspaceRevision } from './workspaceAccess';

/** Bounds on what a hand-off may carry; the form still applies the rule limits. */
const MAX_PHRASES = 50;
const MAX_PHRASE = 1000;

export interface ReportWatchSource {
  reportId: string;
  version: number;
  title: string;
  judgementNumber: number;
  statement: string;
  /** The report's own scope: the draft defaults to it and never to a wider one. */
  teamId: string | null;
}

export interface ReportWatchInput {
  source: ReportWatchSource;
  indicators: readonly string[];
  countries: readonly string[];
  categories: readonly string[];
  /** The report's exact saved area, when it has one that can be represented. */
  geometry: Record<string, unknown> | null;
  /** Why saved area context could not be carried over, if it could not. */
  areaNote: string | null;
}

export interface ReportWatchDraft extends ReportWatchInput {
  id: number;
  actor: string;
}

let pending: ReportWatchDraft | null = null;
let sequence = 0;
const listeners = new Set<() => void>();

function actorKey() {
  const { user, status } = useAuthStore.getState();
  return status === 'authenticated' && user?.is_active
    ? `${user.id}:${user.role}:${workspaceRevision()}`
    : null;
}
function notify() {
  for (const listener of listeners) listener();
}

/** Plain text on one line: control characters removed and whitespace collapsed. */
export function plainText(value: string): string {
  return Array.from(value, (char) => {
    const code = char.charCodeAt(0);
    return code < 32 || code === 127 ? ' ' : char;
  })
    .join('')
    .split(/\s+/)
    .join(' ')
    .trim();
}

export function clearReportWatchDraft(id?: number) {
  if (pending && (id === undefined || pending.id === id)) {
    pending = null;
    notify();
  }
}

export function readReportWatchDraft(): ReportWatchDraft | null {
  return pending?.actor === actorKey() ? pending : null;
}

export function prepareReportWatch(input: ReportWatchInput): ReportWatchDraft {
  const actor = actorKey();
  if (!actor) throw new Error('Sign in before preparing an alert rule.');
  const { source } = input;
  if (!Number.isSafeInteger(source.version) || source.version < 1 || !source.reportId)
    throw new Error('This report version cannot be identified.');
  const indicators = [...new Set(input.indicators.map(plainText).filter(Boolean))];
  if (indicators.length === 0) throw new Error('This judgement has no indicators to watch for.');
  if (indicators.length > MAX_PHRASES || indicators.some((text) => text.length > MAX_PHRASE))
    throw new Error('These indicators are too long to prepare as an alert rule.');
  pending = Object.freeze({
    ...input,
    source: Object.freeze({
      ...source,
      title: plainText(source.title),
      statement: plainText(source.statement),
    }),
    indicators: Object.freeze(indicators),
    countries: Object.freeze([...input.countries]),
    categories: Object.freeze([...input.categories]),
    id: ++sequence,
    actor,
  });
  // One hand-off at a time: a newer report draft replaces a pending map area draft.
  clearAreaWatchDraft();
  notify();
  return pending;
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}
export const useReportWatchDraft = () => useSyncExternalStore(subscribe, readReportWatchDraft);

subscribeWorkspaceAccess(() => clearReportWatchDraft());
// A newer map area hand-off replaces a pending report draft.
subscribeAreaWatchDraft((areaDraft) => {
  if (areaDraft !== null) clearReportWatchDraft();
});
useAuthStore.subscribe((state, previous) => {
  if (
    state.status !== previous.status ||
    state.user?.id !== previous.user?.id ||
    state.user?.role !== previous.user?.role ||
    state.user?.is_active !== previous.user?.is_active
  )
    clearReportWatchDraft();
});

const COUNTRY = /^[A-Z]{2}$/;

function list(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === 'string')
    : [];
}

function savedGeometry(value: unknown): Record<string, unknown> | null {
  if (typeof value !== 'object' || value === null) return null;
  const geometry: unknown = Reflect.get(value, 'geometry');
  return typeof geometry === 'object' && geometry !== null && !Array.isArray(geometry)
    ? (geometry as Record<string, unknown>)
    : null;
}

/**
 * The report's own places as alert rule scope. Only explicit, well-formed values carry over:
 * a malformed or ambiguous saved scope is left for the person to choose, never widened.
 */
export function reportWatchScope(
  scope: Readonly<Record<string, unknown>>,
): Pick<ReportWatchInput, 'countries' | 'categories' | 'geometry' | 'areaNote'> {
  const countries = [
    ...new Set([...list(scope.countries), ...list(scope.country_isos), ...list([scope.country])]),
  ];
  const categories = list(scope.categories).filter((value) =>
    (CATEGORIES as readonly string[]).includes(value),
  );
  const exact = savedGeometry(scope.research_area);
  const origin =
    typeof scope.map_origin === 'object' && scope.map_origin !== null
      ? savedGeometry(Reflect.get(scope.map_origin, 'area'))
      : null;
  const hasArea = Boolean(scope.research_area ?? scope.map_origin);
  const geometry = exact && origin ? null : (exact ?? origin);
  return {
    countries: countries.every((code) => COUNTRY.test(code)) ? countries : [],
    categories,
    geometry,
    areaNote:
      hasArea && geometry === null
        ? "The report's saved area could not be carried over. Choose a location for the alert rule."
        : !countries.every((code) => COUNTRY.test(code))
          ? "The report's saved countries could not be carried over. Choose them for the alert rule."
          : null,
  };
}

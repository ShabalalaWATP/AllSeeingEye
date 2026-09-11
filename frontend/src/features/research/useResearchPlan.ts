import { useState } from 'react';
import { MAX_RESEARCH_HOURS, researchDateError, type ResearchDates } from './ResearchTimeScope';

import { useAccountRequest } from '@/components/account/useAccountRequest';
import { ApiError, describeError } from '@/lib/api/errors';
import { previewResearchPlan } from '@/lib/api/researchPlan';
import type { QueryVariant } from '@/lib/api/researchPlan';
import type { ReportRequest } from '@/lib/api/reports';
import { usePlannedTasks } from './usePlannedTasks';
import { useQueryTransliterations } from './useQueryTransliterations';

export interface PlanScope {
  question: string;
  windowHours: string;
  languages: string[];
  mode: NonNullable<ReportRequest['research_mode']>;
  focus: NonNullable<ReportRequest['research_focus']>;
  subject: string;
  country?: string;
  countries?: string[];
  dates?: ResearchDates;
  webSearch?: boolean;
  history?: { since: string; until: string; projectId?: string };
  area?: {
    viewId: string;
    revisionId: string;
    teamId: string | null;
    since: string;
    until: string;
  };
}
const lines = (text: string) =>
  text
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean);
const invalidTerms = (terms: string[]) =>
  terms.length > 12 || terms.some((term) => term.length > 300) || terms.join('').length > 1000;

/** Preview and submission use the same explicit source IDs and operator-entered terms. */
export function useResearchPlan(scope: PlanScope) {
  const tasks = usePlannedTasks();
  const { candidateHypotheses, plannedTasks } = tasks;
  const [selectedSourceIds, setSourceIds] = useState<string[] | null>(null);
  const sourceIds = selectedSourceIds ?? (scope.history ? ['research-aiddata-projects'] : null);
  const [customTerms, setCustomTerms] = useState(false);
  const [termsText, setTermsText] = useState('');
  const [variantText, setVariantText] = useState<Record<string, string>>({});
  const [variantOriginalText, setVariantOriginalText] = useState<Record<string, string>>({});
  const [snapshot, setSnapshot] = useState<{
    key: string;
    capabilitiesKey: string;
    data: Awaited<ReturnType<typeof previewResearchPlan>>;
  } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const beginRequest = useAccountRequest();
  const suppliedTerms = customTerms ? lines(termsText) : null;
  const terms = scope.history?.projectId
    ? [`aiddata:${scope.history.projectId}`, ...(suppliedTerms ?? [])]
    : suppliedTerms;
  const transliterations = useQueryTransliterations(scope.languages, terms);
  const translations: QueryVariant[] = scope.languages.flatMap((language) => {
    const values = lines(variantText[language] ?? '');
    const originals = lines(variantOriginalText[language] ?? '');
    return values.length
      ? [
          {
            language,
            terms: values,
            kind: 'translation',
            ...(originals.length ? { original_terms: originals } : {}),
          },
        ]
      : [];
  });
  const variants = [...translations, ...transliterations.variants];
  const key = JSON.stringify({
    scope,
    sourceIds,
    terms,
    variants,
    candidateHypotheses,
    plannedTasks,
  });
  const capabilitiesKey = JSON.stringify({ scope, candidateHypotheses });
  const current = snapshot?.key === key && error === null && tasks.error === null;
  const customised =
    customTerms ||
    sourceIds !== null ||
    variants.length > 0 ||
    candidateHypotheses.length > 0 ||
    plannedTasks.length > 0;
  const preview = async () => {
    if (busy) return;
    if (
      translations.some(
        (variant) =>
          variant.original_terms?.length &&
          (variant.original_terms.length !== variant.terms.length ||
            variant.original_terms.some((term) => !terms?.includes(term))),
      )
    ) {
      setError(
        'Link translation originals to exact original search terms, one original per translated line.',
      );
      return;
    }
    if (transliterations.error || variants.length > 8) {
      setError(
        transliterations.error ??
          'Use at most eight translation and transliteration variants combined.',
      );
      return;
    }
    if (tasks.previewError) {
      setError(tasks.previewError);
      return;
    }
    if (sourceIds && tasks.previewTasks.some((task) => !sourceIds.includes(task.source_id))) {
      setError(
        'Every additional search needs a selected source. Update the search or reselect its source.',
      );
      return;
    }
    if (!scope.question.trim() || scope.question.trim().length > 1000 || !scope.languages.length) {
      setError('Enter a question and select at least one search language before previewing.');
      return;
    }
    if ((terms && invalidTerms(terms)) || variants.some((variant) => invalidTerms(variant.terms))) {
      setError(
        'Use up to 12 terms per language, at most 300 characters each and 1,000 characters in total.',
      );
      return;
    }
    if (scope.history) {
      if (scope.history.projectId && !/^[0-9]{1,12}$/.test(scope.history.projectId)) {
        setError('Enter a project ID containing up to 12 digits.');
        return;
      }
      const duration = Date.parse(scope.history.until) - Date.parse(scope.history.since);
      if (!Number.isFinite(duration) || duration <= 0 || duration > 10980 * 86_400_000) {
        setError('Choose valid project years, spanning at most 30 years.');
        return;
      }
    }
    const countries = scope.countries ?? (scope.country ? [scope.country] : []);
    if (
      countries.length > 8 ||
      new Set(countries).size !== countries.length ||
      countries.some((code) => !/^[A-Z]{2}$/.test(code))
    ) {
      setError('Choose up to eight distinct countries before previewing.');
      return;
    }
    const dateScope = scope.area ?? scope.dates;
    if (dateScope && !scope.history) {
      const dateError = researchDateError(dateScope);
      if (dateError) {
        setError(dateError);
        return;
      }
    } else if (
      !scope.history &&
      (!Number.isInteger(Number(scope.windowHours)) ||
        Number(scope.windowHours) <= 0 ||
        Number(scope.windowHours) > MAX_RESEARCH_HOURS)
    ) {
      setError('Choose a valid search period of up to two years.');
      return;
    }
    if (scope.webSearch && (scope.focus === 'document' || scope.focus === 'media')) {
      setError('Fresh web search is unavailable for private attachments.');
      return;
    }
    const signal = beginRequest();
    setBusy(true);
    setError(null);
    const fixed = scope.area ?? scope.history ?? scope.dates;
    const until = fixed ? new Date(fixed.until) : new Date();
    const since = fixed
      ? new Date(fixed.since)
      : new Date(until.getTime() - Number(scope.windowHours) * 3_600_000);
    try {
      const data = await previewResearchPlan(
        {
          ...(scope.area
            ? {
                map_view_id: scope.area.viewId,
                map_revision_id: scope.area.revisionId,
                team_id: scope.area.teamId,
              }
            : {}),
          ...(scope.history ? { time_basis: 'recorded_time' as const } : {}),
          question: scope.question.trim(),
          since: since.toISOString(),
          until: until.toISOString(),
          languages: scope.languages,
          terms: terms ?? [],
          mode: scope.mode,
          focus: scope.focus,
          subject: scope.subject.trim() || null,
          countries,
          research_web_search: scope.webSearch ?? false,
          source_ids: sourceIds,
          query_variants: variants,
          candidate_hypotheses: candidateHypotheses,
          planned_tasks: tasks.previewTasks,
        },
        signal,
      );
      if (
        scope.area &&
        (data.map_origin?.view_id !== scope.area.viewId ||
          data.map_origin.revision_id !== scope.area.revisionId ||
          Date.parse(data.since) !== since.getTime() ||
          Date.parse(data.until) !== until.getTime())
      )
        throw new ApiError(
          422,
          'invalid_request',
          'The preview does not match the selected map revision and interval.',
        );
      if (
        (scope.history || scope.dates) &&
        ((scope.history && data.time_basis !== 'recorded_time') ||
          Date.parse(data.since) !== since.getTime() ||
          Date.parse(data.until) !== until.getTime())
      )
        throw new ApiError(
          422,
          'invalid_request',
          'The preview does not match the historical period.',
        );
      if (!signal.aborted) setSnapshot({ key, data, capabilitiesKey });
    } catch (caught) {
      if (!signal.aborted) setError(describeError(caught));
    } finally {
      if (!signal.aborted) setBusy(false);
    }
  };
  const request: Partial<ReportRequest> = {
    ...(scope.webSearch === undefined ? {} : { research_web_search: scope.webSearch }),
    ...(candidateHypotheses.length ? { research_candidate_hypotheses: candidateHypotheses } : {}),
    ...(plannedTasks.length ? { research_planned_tasks: plannedTasks } : {}),
    ...(sourceIds === null ? {} : { research_source_ids: sourceIds }),
    ...(terms === null ? {} : { research_terms: terms }),
    ...(variants.length ? { research_query_variants: variants } : {}),
  };
  const selectSource = (id: string, selected: boolean) => {
    const existing = sourceIds ?? [
      ...new Set(
        snapshot?.data.tasks.filter((task) => task.selected).map((task) => task.source_id) ?? [],
      ),
    ];
    setSourceIds(
      selected ? [...new Set([...existing, id])] : existing.filter((value) => value !== id),
    );
  };
  return {
    tasks,
    transliterations,
    sourceIds,
    customTerms,
    setCustomTerms,
    termsText,
    setTermsText,
    variantText,
    setVariantText,
    variantOriginalText,
    setVariantOriginalText,
    snapshot: snapshot?.data ?? null,
    registryOptionsCurrent: snapshot?.capabilitiesKey === capabilitiesKey,
    current,
    customised,
    busy,
    error,
    preview,
    request,
    selectSource,
    resetSources: () => setSourceIds(null),
  };
}
export type ResearchPlanState = ReturnType<typeof useResearchPlan>;

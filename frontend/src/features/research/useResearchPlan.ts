import { useState } from 'react';

import { useAccountRequest } from '@/components/account/useAccountRequest';
import { describeError } from '@/lib/api/errors';
import { previewResearchPlan } from '@/lib/api/researchPlan';
import type { ResearchPlan, QueryVariant } from '@/lib/api/researchPlan';
import type { ReportRequest } from '@/lib/api/reports';

export interface PlanScope {
  question: string;
  windowHours: string;
  languages: string[];
  mode: NonNullable<ReportRequest['research_mode']>;
  focus: NonNullable<ReportRequest['research_focus']>;
  subject: string;
  country: string;
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
  const [sourceIds, setSourceIds] = useState<string[] | null>(null);
  const [customTerms, setCustomTerms] = useState(false);
  const [termsText, setTermsText] = useState('');
  const [variantText, setVariantText] = useState<Record<string, string>>({});
  const [snapshot, setSnapshot] = useState<{ key: string; data: ResearchPlan } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const beginRequest = useAccountRequest();
  const terms = customTerms ? lines(termsText) : null;
  const variants: QueryVariant[] = scope.languages.flatMap((language) => {
    const values = lines(variantText[language] ?? '');
    return values.length ? [{ language, terms: values }] : [];
  });
  const key = JSON.stringify({ scope, sourceIds, terms, variants });
  const current = snapshot?.key === key && error === null;
  const customised = customTerms || sourceIds !== null || variants.length > 0;
  const preview = async () => {
    if (busy) return;
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
    const signal = beginRequest();
    setBusy(true);
    setError(null);
    const until = new Date();
    const since = new Date(until.getTime() - Number(scope.windowHours) * 3_600_000);
    try {
      const data = await previewResearchPlan(
        {
          question: scope.question.trim(),
          since: since.toISOString(),
          until: until.toISOString(),
          languages: scope.languages,
          terms: terms ?? [],
          mode: scope.mode,
          focus: scope.focus,
          subject: scope.subject.trim() || null,
          country_iso: scope.country || null,
          source_ids: sourceIds,
          query_variants: variants,
        },
        signal,
      );
      if (!signal.aborted) setSnapshot({ key, data });
    } catch (caught) {
      if (!signal.aborted) setError(describeError(caught));
    } finally {
      if (!signal.aborted) setBusy(false);
    }
  };
  const request: Partial<ReportRequest> = {
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
    sourceIds,
    customTerms,
    setCustomTerms,
    termsText,
    setTermsText,
    variantText,
    setVariantText,
    snapshot: snapshot?.data ?? null,
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

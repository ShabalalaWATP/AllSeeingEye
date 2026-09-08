import { useState } from 'react';
import type { QueryVariant } from '@/lib/api/researchPlan';
import { taskLines } from './usePlannedTasks';

interface Draft {
  original: string;
  transformed: string;
  sourceScript: string;
  targetScript: string;
  method: string;
}
export function useQueryTransliterations(languages: string[], originalTerms: string[] | null) {
  const [drafts, setDrafts] = useState<Record<string, Draft>>({});
  const update = (language: string, change: Partial<Draft>) =>
    setDrafts((current) => ({
      ...current,
      [language]: {
        original: '',
        transformed: '',
        sourceScript: '',
        targetScript: '',
        method: '',
        ...current[language],
        ...change,
      },
    }));
  const variants: QueryVariant[] = languages.flatMap((language) => {
    const draft = drafts[language];
    if (
      !draft ||
      (!draft.original &&
        !draft.transformed &&
        !draft.method &&
        !draft.sourceScript &&
        !draft.targetScript)
    )
      return [];
    return [
      {
        language,
        kind: 'transliteration',
        original_terms: taskLines(draft.original),
        terms: taskLines(draft.transformed),
        ...(draft.sourceScript ? { source_script: draft.sourceScript } : {}),
        ...(draft.targetScript ? { target_script: draft.targetScript } : {}),
        ...(draft.method ? { method: draft.method } : {}),
      },
    ];
  });
  const error = variants.some(
    (value) =>
      !originalTerms?.length ||
      !value.terms.length ||
      value.terms.length !== value.original_terms?.length ||
      !value.method?.trim() ||
      !value.source_script ||
      !value.target_script ||
      value.original_terms.some((term) => !originalTerms.includes(term)) ||
      [value.source_script, value.target_script].some(
        (script) => script && !/^[A-Z][a-z]{3}$/.test(script),
      ),
  )
    ? 'Link each transliterated phrase to an exact original search term, one per line. Supply original terms first. Provide source and target script codes (for example Arab and Latn) and name the method.'
    : null;
  return { drafts, update, variants, error };
}

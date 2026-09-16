import type {
  EconomyExplainer,
  ExplainerGlossaryEntry,
  ExplainerProvenance,
  ExplainerSection,
  ExplainerStatus,
} from '@/lib/api/economyExplainer';

export interface RegionExplainerView {
  status: ExplainerStatus;
  stale: boolean;
  reason: string | null;
  section: ExplainerSection | null;
  glossary: readonly ExplainerGlossaryEntry[];
  provenance: ExplainerProvenance | null;
}

export const emptyExplainer: RegionExplainerView = {
  status: 'empty',
  stale: false,
  reason: null,
  section: null,
  glossary: [],
  provenance: null,
};

/** The written section for one region, or null when nothing checked is available. */
export function regionExplainer(
  data: EconomyExplainer | null | undefined,
  region: string,
): RegionExplainerView {
  if (!data) return emptyExplainer;
  const body = data.explainer;
  const section =
    region === 'WORLD'
      ? (body?.world ?? null)
      : (body?.regions.find((item) => item.id === region)?.section ?? null);
  return {
    status: data.status,
    stale: data.stale,
    reason: data.reason ?? null,
    section,
    glossary: body?.glossary ?? [],
    provenance: data.provenance ?? null,
  };
}

const normalise = (value: string) => value.toLowerCase().replace(/[^a-z]+/g, ' ').trim();

/**
 * The model's everyday wording for one indicator, when it wrote one. The careful
 * project note is always shown first, so a disagreement never replaces it.
 */
export function plainEnglishFor(
  id: string,
  name: string,
  glossary: readonly ExplainerGlossaryEntry[],
): string | null {
  const wanted = [normalise(id), normalise(name)];
  const match = glossary.find((entry) => wanted.includes(normalise(entry.term)));
  return match?.plain_english ?? null;
}

/** Glossary entries that do not simply repeat an indicator already on the page. */
export function generalGlossary(
  glossary: readonly ExplainerGlossaryEntry[],
  indicators: readonly { id: string; name: string }[],
): readonly ExplainerGlossaryEntry[] {
  const covered = new Set(
    indicators.flatMap((item) => [normalise(item.id), normalise(item.name)]),
  );
  return glossary.filter((entry) => !covered.has(normalise(entry.term)));
}

export const STATUS_NOTES: Record<ExplainerStatus, string> = {
  ready: 'Checked against the figures shown on this page.',
  stale: 'The figures have moved on since this was written. A fresh version is written at most once a day.',
  generating: 'A fresh plain-English summary is being written from the current figures.',
  empty: 'No plain-English summary has been written yet.',
  unavailable: 'No plain-English summary is available at the moment.',
  validation_failed:
    'A written summary could not be checked against the figures, so it is not shown. The figures are the source of truth.',
};

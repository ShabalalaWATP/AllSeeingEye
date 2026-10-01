/** The editable collection-plan draft, its shared validation and its request body. */
import type { CollectionPlan, PlanRequest, SirRequest } from '@/lib/api/direction';
import { parseCategories, parseCommaList, parseCountries } from '@/lib/text';

/** Domain limits enforced by the server (MAX_PIRS, MAX_SIRS, MAX_KEYWORDS). */
export const PLAN_LIMITS = { pirs: 8, sirs: 12, keywords: 20, text: 300, name: 120 } as const;

export interface SirDraft {
  key: string;
  text: string;
  keywords: string;
  categories: string;
}

export interface PirDraft {
  key: string;
  text: string;
  sirs: SirDraft[];
}

export interface PlanDraft {
  name: string;
  description: string;
  areaId: string;
  countries: string;
  pirs: PirDraft[];
}

/** Field paths such as `name`, `pirs.0.text` or `pirs.1.sirs.2.keywords` mapped to a reason. */
export type PlanErrors = Record<string, string>;

let sequence = 0;
/** Stable React keys for rows; never sent to the server. */
export function rowKey(): string {
  sequence += 1;
  return `row-${sequence}`;
}

export function emptySir(): SirDraft {
  return { key: rowKey(), text: '', keywords: '', categories: '' };
}

export function emptyPir(): PirDraft {
  return { key: rowKey(), text: '', sirs: [emptySir()] };
}

export function emptyPlanDraft(): PlanDraft {
  return { name: '', description: '', areaId: '', countries: '', pirs: [emptyPir()] };
}

export function draftFromPlan(plan: CollectionPlan): PlanDraft {
  return {
    name: plan.name,
    description: plan.description,
    areaId: plan.aoi_id ?? '',
    countries: plan.countries.join(', '),
    pirs: plan.pirs.map((pir) => ({
      key: rowKey(),
      text: pir.text,
      sirs: pir.sirs.map((sir) => ({
        key: rowKey(),
        text: sir.text,
        keywords: sir.keywords.join(', '),
        categories: sir.categories.join(', '),
      })),
    })),
  };
}

/** The positional codes the server will assign: removing a row renumbers later rows. */
export function pirCode(index: number): string {
  return `PIR-${index + 1}`;
}

export function sirCode(pirIndex: number, sirIndex: number): string {
  return `SIR-${pirIndex + 1}.${sirIndex + 1}`;
}

function unknownCategories(text: string): string[] {
  const known = new Set<string>(parseCategories(text));
  return parseCommaList(text).filter((entry) => !known.has(entry.toLowerCase()));
}

/** Rules shared by creating and editing; the server repeats them. */
export function validatePlanDraft(draft: PlanDraft, areaAvailable: boolean): PlanErrors {
  const errors: PlanErrors = {};
  if (draft.name.trim() === '') errors.name = 'Enter a plan name.';
  if (draft.areaId !== '' && !areaAvailable)
    errors.areaId = 'This area is not available in the plan workspace. Choose another or No area.';
  const invalidCountries = parseCommaList(draft.countries).filter(
    (code) => !/^[A-Za-z]{2}$/.test(code),
  );
  if (invalidCountries.length > 0)
    errors.countries = `Use two-letter ISO codes. Check: ${invalidCountries.join(', ')}.`;
  if (draft.pirs.length === 0) errors.pirs = 'Add at least one priority intelligence requirement.';
  if (draft.pirs.length > PLAN_LIMITS.pirs)
    errors.pirs = `A plan holds at most ${PLAN_LIMITS.pirs} priority intelligence requirements.`;
  draft.pirs.forEach((pir, index) => {
    if (pir.text.trim() === '') errors[`pirs.${index}.text`] = 'Enter the requirement question.';
    if (pir.sirs.length > PLAN_LIMITS.sirs)
      errors[`pirs.${index}.sirs`] = `At most ${PLAN_LIMITS.sirs} specific requirements.`;
    pir.sirs.forEach((sir, position) => {
      const path = `pirs.${index}.sirs.${position}`;
      if (sir.text.trim() === '') errors[`${path}.text`] = 'Enter the specific requirement.';
      if (parseCommaList(sir.keywords).length > PLAN_LIMITS.keywords)
        errors[`${path}.keywords`] = `Use at most ${PLAN_LIMITS.keywords} keywords.`;
      const unknown = unknownCategories(sir.categories);
      if (unknown.length > 0)
        errors[`${path}.categories`] = `Unknown categories: ${unknown.join(', ')}.`;
    });
  });
  return errors;
}

const SHOWN_BESIDE_A_FIELD =
  /^(name|countries|pirs(\.\d+\.(text|sirs(\.\d+\.(text|keywords|categories))?))?)$/;

/**
 * Server validation reasons, keyed by dotted request paths, as draft errors. Request paths
 * already match the draft's (`pirs.0.sirs.1.text`); `aoi_id` and `countries.N` are renamed.
 */
export function planErrorsFromServer(fields: Readonly<Record<string, string>>): PlanErrors {
  const errors: PlanErrors = {};
  for (const [path, reason] of Object.entries(fields)) {
    const key = path === 'aoi_id' ? 'areaId' : path.startsWith('countries.') ? 'countries' : path;
    errors[key] ??= reason;
  }
  return errors;
}

/** Reasons no control shows, so the summary can list them instead of dropping them. */
export function unplacedPlanErrors(errors: PlanErrors): [string, string][] {
  return Object.entries(errors).filter(([key]) => !SHOWN_BESIDE_A_FIELD.test(key));
}

function sirRequest(sir: SirDraft): SirRequest {
  const request: SirRequest = { text: sir.text.trim() };
  const keywords = parseCommaList(sir.keywords);
  if (keywords.length > 0) request.keywords = keywords;
  const categories = parseCategories(sir.categories);
  if (categories.length > 0) request.categories = categories;
  return request;
}

/** The body shared by create and update; scope and the revision are added by the caller. */
export function planRequest(
  draft: PlanDraft,
  teamId: string | null,
  enabled: boolean,
): PlanRequest {
  return {
    name: draft.name.trim(),
    enabled,
    ...(teamId ? { team_id: teamId } : {}),
    description: draft.description.trim(),
    aoi_id: draft.areaId === '' ? null : draft.areaId,
    countries: parseCountries(draft.countries),
    pirs: draft.pirs.map((pir) => ({ text: pir.text.trim(), sirs: pir.sirs.map(sirRequest) })),
  };
}

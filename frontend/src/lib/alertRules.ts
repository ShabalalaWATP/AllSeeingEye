/**
 * Alert rule form values, their validation and the plain-words summary shown before saving.
 *
 * Nothing here drops a value it does not recognise. An unknown country, category or an
 * overlong keyword is reported as a problem, because dropping it would quietly widen what
 * the rule watches (an empty list means unrestricted on the server). Unrestricted scope is
 * only ever an explicit choice: `worldwide` or `all`.
 */
import type { components } from '@/lib/api/types.gen';
import type { Indicator } from '@/lib/api/warning';
import { CATEGORIES } from '@/lib/api/eventSchemas';
import type { Category } from '@/lib/api/eventSchemas';
import { CATEGORY_STYLES } from '@/lib/categories';
import { parseCommaList } from '@/lib/text';

export type IndicatorRequest = components['schemas']['IndicatorIn'];
export type IndicatorUpdateRequest = components['schemas']['IndicatorUpdateIn'];

/** The server's ranges (`IndicatorIn`), checked against the OpenAPI schema in a test. */
export const COOLDOWN_RANGE = { min: 1, max: 1440 } as const;
export const MAX_KEYWORDS = 20;
export const MAX_KEYWORD_LENGTH = 60;
export const MAX_COUNTRIES = 50;
export const MAX_NAME = 120;
export const MAX_DESCRIPTION = 1000;
const MAX_THRESHOLD = 10_000;

export const WINDOWS = [
  { value: '60', label: '1 hour' },
  { value: '360', label: '6 hours' },
  { value: '1440', label: '1 day' },
  { value: '10080', label: '7 days' },
];

export type LocationMode = 'countries' | 'worldwide' | 'area' | 'shape';
export type CategoryMode = 'all' | 'specific';

export interface RuleFields {
  name: string;
  description: string;
  planId: string;
  locationMode: LocationMode;
  countries: string[];
  categoryMode: CategoryMode;
  categories: string[];
  keywords: string;
  threshold: string;
  ratio: string;
  baselineDays: string;
  window: string;
  cooldown: string;
  severityFloor: string;
  template: string;
  enabled: boolean;
}

/** A request field the form can show a problem beside. */
export type RuleProblemField =
  | 'name'
  | 'description'
  | 'countries'
  | 'categories'
  | 'keywords'
  | 'threshold'
  | 'baseline_ratio'
  | 'baseline_days'
  | 'cooldown_minutes'
  | 'severity_floor';

export function emptyRuleFields(): RuleFields {
  return {
    name: '',
    description: '',
    planId: '',
    locationMode: 'countries',
    countries: [],
    categoryMode: 'all',
    categories: [],
    keywords: '',
    threshold: '1',
    ratio: '',
    baselineDays: '30',
    window: '360',
    cooldown: '60',
    severityFloor: '0',
    template: '',
    enabled: true,
  };
}

/** Every saved value, so an edit sends back the fields it does not show unchanged. */
export function ruleFieldsFromIndicator(rule: Indicator): RuleFields {
  return {
    name: rule.name,
    description: rule.description,
    planId: rule.plan_id ?? '',
    locationMode: rule.research_area
      ? 'shape'
      : rule.bbox !== null
        ? 'area'
        : rule.countries.length > 0
          ? 'countries'
          : 'worldwide',
    countries: [...rule.countries],
    categoryMode: rule.categories.length > 0 ? 'specific' : 'all',
    categories: [...rule.categories],
    keywords: rule.keywords.join(', '),
    threshold: String(rule.threshold),
    ratio: rule.baseline_ratio == null ? '' : String(rule.baseline_ratio),
    baselineDays: String(rule.baseline_days ?? 30),
    window: String(rule.window_minutes),
    cooldown: String(rule.cooldown_minutes),
    severityFloor: String(rule.severity_floor),
    template: rule.report_template ?? '',
    enabled: rule.enabled,
  };
}

/** Distinct non-empty keywords, in order. Long ones are kept so they can be reported. */
export function splitKeywords(text: string): string[] {
  return [...new Set(parseCommaList(text).map((word) => word.split(/\s+/).join(' ')))];
}

const isCategory = (value: string) => (CATEGORIES as readonly string[]).includes(value);

function inRange(text: string, min: number, max: number, integer: boolean): boolean {
  const value = Number(text);
  return (
    text.trim() !== '' &&
    Number.isFinite(value) &&
    (!integer || Number.isInteger(value)) &&
    value >= min &&
    value <= max
  );
}

/** What stops the rule being saved, by request field. Empty when it can be submitted. */
export function ruleProblems(
  fields: RuleFields,
  context: { knownCountries: ReadonlySet<string> | null },
): Partial<Record<RuleProblemField, string>> {
  const problems: Partial<Record<RuleProblemField, string>> = {};
  if (fields.name.trim() === '') problems.name = 'Enter a name for the alert rule.';
  else if (fields.name.trim().length > MAX_NAME)
    problems.name = `Shorten the name to ${String(MAX_NAME)} characters or fewer.`;
  if (fields.description.trim().length > MAX_DESCRIPTION)
    problems.description = `Shorten the notes to ${String(MAX_DESCRIPTION)} characters or fewer.`;
  if (fields.locationMode === 'countries') {
    const unknown = fields.countries.filter(
      (code) => !/^[A-Z]{2}$/.test(code) || context.knownCountries?.has(code) === false,
    );
    if (unknown.length > 0) problems.countries = `Remove unknown countries: ${unknown.join(', ')}.`;
    else if (context.knownCountries === null)
      problems.countries = 'The country list could not be loaded. Reload the page and try again.';
    else if (fields.countries.length === 0)
      problems.countries =
        'Choose at least one country, or choose Worldwide for no location limit.';
    else if (fields.countries.length > MAX_COUNTRIES)
      problems.countries = `Choose at most ${String(MAX_COUNTRIES)} countries.`;
  }
  if (fields.categoryMode === 'specific') {
    const unknown = fields.categories.filter((value) => !isCategory(value));
    if (unknown.length > 0)
      problems.categories = `Remove unknown categories: ${unknown.join(', ')}.`;
    else if (fields.categories.length === 0)
      problems.categories = 'Choose at least one category, or choose All event categories.';
  }
  const keywords = splitKeywords(fields.keywords);
  const long = keywords.filter((word) => word.length > MAX_KEYWORD_LENGTH).length;
  if (keywords.length > MAX_KEYWORDS)
    problems.keywords = `Use at most ${String(MAX_KEYWORDS)} keywords (${String(keywords.length)} entered).`;
  else if (long > 0)
    problems.keywords = `Shorten each keyword to ${String(MAX_KEYWORD_LENGTH)} characters or fewer (${String(long)} ${long === 1 ? 'is' : 'are'} longer).`;
  if (!inRange(fields.threshold, 1, MAX_THRESHOLD, true))
    problems.threshold = 'Enter a whole number from 1 to 10000.';
  const ratio = fields.ratio ?? '';
  if (ratio !== '' && (!inRange(ratio, 1, 100, false) || Number(ratio) <= 1))
    problems.baseline_ratio = 'Enter a ratio above 1 and no greater than 100, or leave it empty.';
  if (!inRange(fields.baselineDays ?? '30', 7, 30, true))
    problems.baseline_days = 'Enter whole days from 7 to 30.';
  if (!inRange(fields.cooldown, COOLDOWN_RANGE.min, COOLDOWN_RANGE.max, true))
    problems.cooldown_minutes = 'Enter whole minutes from 1 to 1440 (24 hours).';
  if (!inRange(fields.severityFloor, 0, 1, false))
    problems.severity_floor = 'Enter a number from 0 to 1.';
  return problems;
}

export interface RuleScope {
  teamId: string;
  bbox: [number, number, number, number] | undefined;
  geometry: Record<string, unknown> | undefined;
}

/** The request for these values. Only call it once `ruleProblems` is empty. */
export function ruleRequest(fields: RuleFields, scope: RuleScope): IndicatorRequest {
  const shape = fields.locationMode === 'shape' && scope.geometry !== undefined;
  return {
    ...(scope.teamId ? { team_id: scope.teamId } : {}),
    ...(fields.planId ? { plan_id: fields.planId } : {}),
    name: fields.name.trim(),
    description: fields.description.trim(),
    countries: fields.locationMode === 'countries' ? [...fields.countries] : [],
    ...(shape ? { research_area: { geometry: { ...scope.geometry } } } : {}),
    ...(fields.locationMode === 'area' && scope.bbox ? { bbox: scope.bbox } : {}),
    categories:
      fields.categoryMode === 'specific'
        ? (fields.categories.filter(isCategory) as Category[])
        : [],
    keywords: splitKeywords(fields.keywords),
    threshold: Number(fields.threshold),
    baseline_ratio: fields.ratio ? Number(fields.ratio) : null,
    baseline_days: Number(fields.baselineDays ?? '30'),
    window_minutes: fields.ratio ? 60 : Number(fields.window),
    cooldown_minutes: Number(fields.cooldown),
    severity_floor: Number(fields.severityFloor),
    report_template: shape || fields.template === '' ? null : fields.template,
    enabled: fields.enabled,
  };
}

export function windowLabel(minutes: number): string {
  const plural = (count: number, unit: string) =>
    `${String(count)} ${unit}${count === 1 ? '' : 's'}`;
  if (minutes % 1440 === 0) return plural(minutes / 1440, 'day');
  if (minutes % 60 === 0) return plural(minutes / 60, 'hour');
  return plural(minutes, 'minute');
}

export interface SummaryRow {
  label: string;
  text: string;
}

/** What the rule will do, in words, so the person can check it before saving. */
export function ruleSummary(
  fields: RuleFields,
  names: {
    countryName: (code: string) => string;
    templateName: (id: string) => string;
    bbox: readonly number[] | undefined;
  },
): SummaryRow[] {
  const geography = {
    worldwide: 'Worldwide: no location restriction',
    countries:
      fields.countries.length === 0
        ? 'No countries chosen yet'
        : fields.countries.map((code) => `${names.countryName(code)} (${code})`).join(', '),
    area: names.bbox
      ? `Map rectangle: ${(['west', 'south', 'east', 'north'] as const)
          .map((edge, index) => `${edge} ${(names.bbox?.[index] ?? 0).toFixed(2)}`)
          .join(', ')}; only items with a map point inside count`
      : 'Map rectangle with incomplete bounds',
    shape: 'Exact drawn shape; only precisely located items count',
  }[fields.locationMode];
  const keywords = splitKeywords(fields.keywords);
  const floor = Number(fields.severityFloor);
  const shape = fields.locationMode === 'shape';
  return [
    { label: 'Geography', text: geography },
    {
      label: 'Categories',
      text:
        fields.categoryMode === 'all'
          ? 'All event categories'
          : fields.categories
              .map((value) =>
                isCategory(value) ? CATEGORY_STYLES[value as Category].label : value,
              )
              .join(', ') || 'No categories chosen yet',
    },
    {
      label: 'Keywords',
      text:
        keywords.length === 0
          ? 'Any matching item; no keyword filter'
          : `Title or summary contains any of: ${keywords.map((word) => `“${word}”`).join(', ')} (literal, not case sensitive)`,
    },
    {
      label: 'Threshold',
      text: `${fields.threshold} or more matching items`,
    },
    ...(fields.ratio
      ? [
          {
            label: 'Baseline ratio',
            text: `At least ${fields.ratio} times the ${fields.baselineDays ?? '30'}-day sampled hourly mean; requires seven days and 168 sampled hours, with a positive mean`,
          },
        ]
      : []),
    {
      label: 'Time window',
      text: `The last ${windowLabel(fields.ratio ? 60 : Number(fields.window))}`,
    },
    {
      label: 'Severity floor',
      text:
        floor > 0
          ? `Only items rated ${String(floor)} or higher (unrated items count as 0)`
          : 'None: every item counts, including unrated ones',
    },
    { label: 'Cooldown', text: `${windowLabel(Number(fields.cooldown))} between alerts` },
    {
      label: 'Report',
      text:
        shape || fields.template === ''
          ? 'No report; alerts only'
          : `Generates ${names.templateName(fields.template)} when it fires`,
    },
  ];
}

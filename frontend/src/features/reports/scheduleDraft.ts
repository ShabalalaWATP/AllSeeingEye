import type { Category } from '@/lib/api/eventSchemas';
import type { ReportTemplate } from '@/lib/api/reports';
import type { Schedule, ScheduleRequest } from '@/lib/api/schedules';
import { MAX_REGIONS, type Region } from '@/lib/regions';
import { MAX_THEMES } from '@/lib/themes';
import { scheduleWindowHours, type Cadence, type LookbackUnit } from './scheduleTimingPolicy';

export interface ScheduleDraft {
  name: string;
  template: string;
  selectedCountries: string[];
  regions: Region[];
  themes: Category[];
  question: string;
  notifyOnChange: boolean;
  researchMode: NonNullable<ScheduleRequest['research_mode']>;
  languages: string;
  focus: NonNullable<ScheduleRequest['research_focus']>;
  subject: string;
  webSearch: boolean;
  sourceIds: string[] | null;
  hour: string;
  cadence: Cadence;
  weekday: string;
  anchorMonth: string;
  avoidRepetition: boolean;
  conflictId: string;
  hazard: string;
  researchArea: NonNullable<ScheduleRequest['research_area']> | null;
  discloseArea: boolean;
  monthday: string;
  lookbackUnit: LookbackUnit;
  lookback: string;
}
export interface ScheduleContext {
  templates: readonly ReportTemplate[];
  scope: { teamId: string; ready: boolean };
  selectedPlan: string;
  invalidPlan: boolean;
  initial?: Schedule | undefined;
}

export interface ScheduleIssue {
  field: string;
  message: string;
  advanced?: boolean;
}

/** Keep form validation and submitted scope derived from the same normalised draft. */
export function evaluateSchedule(draft: ScheduleDraft, context: ScheduleContext) {
  const {
    name,
    template,
    selectedCountries,
    regions,
    themes,
    question,
    notifyOnChange,
    researchMode,
    languages,
    focus,
    subject,
    webSearch,
    sourceIds,
    hour,
    cadence,
    weekday,
    anchorMonth,
    avoidRepetition,
    conflictId,
    hazard,
    researchArea,
    discloseArea,
    monthday,
    lookbackUnit,
    lookback,
  } = draft;
  const { templates, scope, selectedPlan, invalidPlan, initial } = context;
  const windowHours = scheduleWindowHours(lookback, lookbackUnit);
  const product = templates.find((item) => item.id === template);
  const needsQuestion = product?.needs_question === true;
  const activeResearch = needsQuestion;
  const languageCodes = [
    ...new Set(
      languages
        .split(',')
        .map((code) => code.trim().toLowerCase())
        .filter(Boolean),
    ),
  ];
  const validLanguages =
    languageCodes.length >= 1 &&
    languageCodes.length <= 8 &&
    languageCodes.every((code) => /^[a-z]{2,3}(-[a-z]{2,4})?$/.test(code));
  const subjectScoped = activeResearch && focus !== 'general';
  const boundaryScoped = activeResearch && researchArea !== null;
  const countriesInScope = subjectScoped || boundaryScoped ? [] : selectedCountries;
  const regionsInScope = subjectScoped || boundaryScoped ? [] : regions;
  const invalidQuestion =
    needsQuestion &&
    ((!question.trim() && (!selectedPlan || activeResearch)) ||
      (activeResearch && !validLanguages) ||
      (subjectScoped && !subject.trim()));
  const validWindow =
    windowHours === null ||
    (Number.isInteger(Number(lookback)) && windowHours >= 1 && windowHours <= 17520);
  const invalidCountry = product?.needs_country === true && countriesInScope.length !== 1;
  const issues: ScheduleIssue[] = [
    ...(!name.trim()
      ? [{ field: 'Subscription name', message: 'Enter a subscription name.' }]
      : []),
    ...(!scope.ready
      ? [{ field: 'Workspace', message: 'Choose an available workspace.', advanced: true }]
      : []),
    ...(!product ? [{ field: 'Product', message: 'Choose a product.', advanced: true }] : []),
    ...(invalidPlan
      ? [
          {
            field: 'Collection plan',
            message: 'Choose an available collection plan.',
            advanced: true,
          },
        ]
      : []),
    ...(needsQuestion && !question.trim() && (!selectedPlan || activeResearch)
      ? [{ field: 'Question', message: 'Enter a question.' }]
      : []),
    ...(activeResearch && !validLanguages
      ? [
          {
            field: 'Research languages',
            message: 'Enter one to eight valid language codes.',
            advanced: true,
          },
        ]
      : []),
    ...(subjectScoped && !subject.trim()
      ? [{ field: 'Research subject', message: 'Enter a research subject.', advanced: true }]
      : []),
    ...(invalidCountry ? [{ field: 'Nation', message: 'Choose one nation.' }] : []),
    ...(countriesInScope.length > 8
      ? [{ field: 'Countries', message: 'Choose no more than eight countries.' }]
      : []),
    ...(regionsInScope.length > MAX_REGIONS
      ? [{ field: 'Regions', message: `Choose no more than ${MAX_REGIONS} regions.` }]
      : []),
    ...(themes.length > MAX_THEMES
      ? [{ field: 'Themes', message: `Choose no more than ${MAX_THEMES} themes.` }]
      : []),
    ...(!validWindow
      ? [{ field: 'Search period', message: 'Choose a search period within two years.' }]
      : []),
    ...(boundaryScoped && initial?.enabled !== false && !discloseArea
      ? [{ field: 'Area disclosure', message: 'Allow providers to receive the saved area.' }]
      : []),
  ];
  const invalid = issues.length > 0;
  const request: ScheduleRequest = {
    ...(scope.teamId ? { team_id: scope.teamId } : {}),
    ...(selectedPlan && !boundaryScoped ? { plan_id: selectedPlan } : {}),
    ...(needsQuestion && question.trim() ? { question: question.trim() } : {}),
    ...(activeResearch
      ? {
          research_mode: researchMode,
          research_languages: languageCodes,
          research_subject: focus === 'general' ? null : subject.trim() || null,
          research_source_ids: sourceIds,
        }
      : {}),
    research_focus: activeResearch ? focus : 'general',
    notify_on_change: needsQuestion && notifyOnChange,
    name: name.trim(),
    enabled: initial?.enabled ?? true,
    template_id: template,
    country_iso: countriesInScope.length === 1 ? (countriesInScope[0] ?? null) : null,
    country_isos: countriesInScope,
    regions: regionsInScope,
    categories: needsQuestion ? themes : [],
    research_web_search: activeResearch && webSearch,
    window_hours: windowHours,
    hour_utc: Number(hour),
    timezone: initial?.timezone ?? 'UTC',
    local_hour: Number(hour),
    local_minute: initial?.local_minute ?? 0,
    collection_policy: initial?.collection_policy ?? 'rolling_snapshot',
    cadence,
    anchor_month: Number(anchorMonth),
    avoid_repetition: avoidRepetition,
    conflict_id: needsQuestion && !subjectScoped && !researchArea ? conflictId || null : null,
    hazard: needsQuestion && !subjectScoped && !researchArea ? hazard || null : null,
    research_area: activeResearch && !subjectScoped ? researchArea : null,
    disclose_area_to_provider: boundaryScoped && !subjectScoped && discloseArea,
    weekday: Number(weekday),
    monthday: Number(monthday),
  };
  return {
    product,
    needsQuestion,
    activeResearch,
    languageCodes,
    validLanguages,
    subjectScoped,
    boundaryScoped,
    countriesInScope,
    regionsInScope,
    invalidQuestion,
    validWindow,
    invalid,
    issues,
    windowHours,
    request,
  };
}

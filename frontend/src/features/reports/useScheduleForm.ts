import { useState, type SyntheticEvent } from 'react';
import type { Category } from '@/lib/api/eventSchemas';
import type { CollectionPlan } from '@/lib/api/direction';
import type { ReportTemplate } from '@/lib/api/reports';
import type { Schedule, ScheduleRequest } from '@/lib/api/schedules';
import { useWorkspaceSelection, type Workspaces } from '@/lib/hooks/useWorkspaces';
import { MAX_REGIONS, type Region } from '@/lib/regions';
import { MAX_THEMES } from '@/lib/themes';
import type { Cadence, LookbackUnit } from './ScheduleTiming';

const CADENCE_DAYS: Record<Cadence, number> = {
  daily: 1,
  weekdays: 3,
  weekly: 7,
  monthly: 31,
  quarterly: 92,
  semiannual: 184,
  annual: 366,
};

export interface ScheduleFormStateProps {
  templates: readonly ReportTemplate[];
  plans: readonly CollectionPlan[];
  workspaces: Workspaces;
  busy: boolean;
  initial?: Schedule | undefined;
  draftQuestion?: string | undefined;
  draftCountry?: string | undefined;
  onSubmit: (request: ScheduleRequest) => void;
}

export interface ScheduleIssue {
  field: string;
  message: string;
  advanced?: boolean;
}

/**
 * A schedule reuses normal research choices and evaluates its time window at each run.
 *
 * Research always runs at the chosen depth; the only source choice a subscriber makes
 * is whether each run also searches the web. A saved schedule from before that rule had
 * no depth at all and is read back as Basic.
 */
export function useScheduleForm({
  templates,
  plans,
  workspaces,
  busy,
  initial,
  draftQuestion = '',
  draftCountry = '',
  onSubmit,
}: ScheduleFormStateProps) {
  const selection = useWorkspaceSelection(workspaces);
  const teamId = initial ? (initial.team_id ?? '') : selection.teamId;
  const scope = {
    ...selection,
    teamId,
    ready: initial
      ? !workspaces.loading && (!teamId || workspaces.teams.some((item) => item.team.id === teamId))
      : selection.ready,
  };
  const [planId, setPlanId] = useState(initial?.plan_id ?? '');
  const matchingPlans = plans.filter(
    (plan) => plan.enabled && (plan.team_id ?? '') === scope.teamId,
  );
  const selectedPlan = matchingPlans.some((plan) => plan.id === planId) ? planId : '';
  const invalidPlan = planId !== '' && selectedPlan === '';
  const [name, setName] = useState(initial?.name ?? '');
  const [template, setTemplate] = useState(initial?.template_id ?? 'ask');
  const [selectedCountries, setCountries] = useState<string[]>(
    initial?.country_isos.length
      ? initial.country_isos
      : initial?.country_iso
        ? [initial.country_iso]
        : /^[A-Z]{2}$/.test(draftCountry.toUpperCase())
          ? [draftCountry.toUpperCase()]
          : [],
  );
  const [regions, setRegions] = useState<Region[]>(initial?.regions ?? []);
  const [themes, setThemes] = useState<Category[]>(initial?.categories ?? []);
  const [question, setQuestion] = useState(initial?.question ?? draftQuestion.slice(0, 1000));
  const [notifyOnChange, setNotifyOnChange] = useState(initial?.notify_on_change ?? true);
  const [researchMode, setResearchMode] = useState<NonNullable<ScheduleRequest['research_mode']>>(
    initial?.research_mode ?? 'quick',
  );
  const [languages, setLanguages] = useState(initial?.research_languages.join(', ') ?? 'en');
  const [focus, setFocus] = useState<NonNullable<ScheduleRequest['research_focus']>>(
    initial?.research_focus ?? 'general',
  );
  const [subject, setSubject] = useState(initial?.research_subject ?? '');
  const [webSearch, setWebSearch] = useState(initial?.research_web_search ?? false);
  const [sourceIds, setSourceIds] = useState<string[] | null>(initial?.research_source_ids ?? null);
  const [chooseSources, setChooseSources] = useState(false);
  const [hour, setHour] = useState(String(initial?.hour_utc ?? 6));
  const [cadence, updateCadence] = useState<Cadence>(
    (initial?.cadence as Cadence | undefined) ?? 'weekly',
  );
  const [weekday, setWeekday] = useState(String(initial?.weekday ?? 0));
  const [anchorMonth, setAnchorMonth] = useState(
    String(initial?.anchor_month ?? new Date().getUTCMonth() + 1),
  );
  const [avoidRepetition, setAvoidRepetition] = useState(initial?.avoid_repetition ?? true);
  const [conflictId, setConflictId] = useState(initial?.conflict_id ?? '');
  const [hazard, setHazard] = useState(initial?.hazard ?? '');
  const [researchArea, setResearchArea] = useState<NonNullable<
    ScheduleRequest['research_area']
  > | null>(initial?.research_area ? { geometry: initial.research_area.geometry } : null);
  const [discloseArea, setDiscloseArea] = useState(initial?.disclose_area_to_provider ?? false);
  const [monthday, setMonthday] = useState(String(initial?.monthday ?? 1));
  const [lookbackUnit, setLookbackUnit] = useState<LookbackUnit>(
    initial?.window_hours === null
      ? 'default'
      : initial && initial.window_hours % 24 !== 0
        ? 'hours'
        : 'days',
  );
  const [lookback, setLookback] = useState(
    String(
      initial?.window_hours === null
        ? 7
        : initial && initial.window_hours % 24 !== 0
          ? initial.window_hours
          : (initial?.window_hours ?? 168) / 24,
    ),
  );
  const setCadence = (value: Cadence) => {
    if (!initial && lookbackUnit === 'days' && Number(lookback) === CADENCE_DAYS[cadence])
      setLookback(String(CADENCE_DAYS[value]));
    updateCadence(value);
  };
  const windowHours =
    lookbackUnit === 'default' ? null : Number(lookback) * (lookbackUnit === 'days' ? 24 : 1);
  const changeLookbackUnit = (value: LookbackUnit) => {
    setLookbackUnit(value);
    if (value !== 'default')
      setLookback(
        String(
          value === 'days'
            ? Math.max(1, Math.ceil((windowHours ?? 168) / 24))
            : (windowHours ?? 168),
        ),
      );
  };
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
  const submit = (event: SyntheticEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (invalid || busy) return;
    onSubmit({
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
    });
  };
  return {
    scope,
    anchorMonth,
    setAnchorMonth,
    avoidRepetition,
    setAvoidRepetition,
    conflictId,
    setConflictId,
    hazard,
    setHazard,
    researchArea,
    setResearchArea,
    discloseArea,
    setDiscloseArea,
    matchingPlans,
    selectedPlan,
    invalidPlan,
    name,
    setName,
    template,
    setTemplate,
    question,
    setQuestion,
    notifyOnChange,
    setNotifyOnChange,
    researchMode,
    setResearchMode,
    languages,
    setLanguages,
    focus,
    setFocus,
    subject,
    setSubject,
    webSearch,
    setWebSearch,
    sourceIds,
    setSourceIds,
    chooseSources,
    setChooseSources,
    hour,
    setHour,
    cadence,
    setCadence,
    weekday,
    setWeekday,
    monthday,
    setMonthday,
    lookback,
    setLookback,
    lookbackUnit,
    changeLookbackUnit,
    previewLookbackDays: (windowHours ?? CADENCE_DAYS[cadence] * 24) / 24,
    product,
    needsQuestion,
    activeResearch,
    languageCodes,
    validLanguages,
    subjectScoped,
    boundaryScoped,
    countriesInScope,
    setCountries,
    regions: regionsInScope,
    setRegions,
    themes,
    setThemes,
    invalidQuestion,
    validWindow,
    invalid,
    issues,
    submit,
    setPlanId,
  };
}
export type ScheduleFormState = ReturnType<typeof useScheduleForm>;

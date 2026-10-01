import { evaluateSchedule } from './scheduleDraft';
import {
  CADENCE_DAYS,
  convertLookback,
  lookbackForCadence,
  type Cadence,
  type LookbackUnit,
} from './scheduleTimingPolicy';
import { type SyntheticEvent } from 'react';
import type { Category } from '@/lib/api/eventSchemas';
import type { CollectionPlan } from '@/lib/api/direction';
import type { ReportTemplate } from '@/lib/api/reports';
import type { Schedule, ScheduleRequest } from '@/lib/api/schedules';
import { draftForms, useDraftState, useHasDraft } from '@/lib/formDrafts';
import { useUnloadWarning } from '@/lib/hooks/useUnloadWarning';
import { useWorkspaceSelection, type Workspaces } from '@/lib/hooks/useWorkspaces';
import type { Region } from '@/lib/regions';

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
  // A new subscription keeps an in-memory draft per link context; edits and copies do not.
  const form = initial ? null : draftForms.subscription(draftQuestion, draftCountry);
  const selection = useWorkspaceSelection(workspaces, form);
  useUnloadWarning(useHasDraft(form));
  const teamId = initial ? (initial.team_id ?? '') : selection.teamId;
  const scope = {
    ...selection,
    teamId,
    ready: initial
      ? !workspaces.loading && (!teamId || workspaces.teams.some((item) => item.team.id === teamId))
      : selection.ready,
  };
  const [planId, setPlanId] = useDraftState(form, 'planId', initial?.plan_id ?? '');
  const matchingPlans = plans.filter(
    (plan) => plan.enabled && (plan.team_id ?? '') === scope.teamId,
  );
  const selectedPlan = matchingPlans.some((plan) => plan.id === planId) ? planId : '';
  const invalidPlan = planId !== '' && selectedPlan === '';
  const [name, setName] = useDraftState(form, 'name', initial?.name ?? '');
  const [template, setTemplate] = useDraftState(form, 'template', initial?.template_id ?? 'ask');
  const [selectedCountries, setCountries] = useDraftState<string[]>(
    form,
    'selectedCountries',
    initial?.country_isos.length
      ? initial.country_isos
      : initial?.country_iso
        ? [initial.country_iso]
        : /^[A-Z]{2}$/.test(draftCountry.toUpperCase())
          ? [draftCountry.toUpperCase()]
          : [],
  );
  const [regions, setRegions] = useDraftState<Region[]>(form, 'regions', initial?.regions ?? []);
  const [themes, setThemes] = useDraftState<Category[]>(form, 'themes', initial?.categories ?? []);
  const [question, setQuestion] = useDraftState(
    form,
    'question',
    initial?.question ?? draftQuestion.slice(0, 1000),
  );
  const [notifyOnChange, setNotifyOnChange] = useDraftState(
    form,
    'notifyOnChange',
    initial?.notify_on_change ?? true,
  );
  const [researchMode, setResearchMode] = useDraftState<
    NonNullable<ScheduleRequest['research_mode']>
  >(form, 'researchMode', initial?.research_mode ?? 'quick');
  const [languages, setLanguages] = useDraftState(
    form,
    'languages',
    initial?.research_languages.join(', ') ?? 'en',
  );
  const [focus, setFocus] = useDraftState<NonNullable<ScheduleRequest['research_focus']>>(
    form,
    'focus',
    initial?.research_focus ?? 'general',
  );
  const [subject, setSubject] = useDraftState(form, 'subject', initial?.research_subject ?? '');
  const [webSearch, setWebSearch] = useDraftState(
    form,
    'webSearch',
    initial?.research_web_search ?? false,
  );
  const [sourceIds, setSourceIds] = useDraftState<string[] | null>(
    form,
    'sourceIds',
    initial?.research_source_ids ?? null,
  );
  const [chooseSources, setChooseSources] = useDraftState(form, 'chooseSources', false);
  const [hour, setHour] = useDraftState(form, 'hour', String(initial?.hour_utc ?? 6));
  const [cadence, updateCadence] = useDraftState<Cadence>(
    form,
    'cadence',
    (initial?.cadence as Cadence | undefined) ?? 'weekly',
  );
  const [weekday, setWeekday] = useDraftState(form, 'weekday', String(initial?.weekday ?? 0));
  const [anchorMonth, setAnchorMonth] = useDraftState(
    form,
    'anchorMonth',
    String(initial?.anchor_month ?? new Date().getUTCMonth() + 1),
  );
  const [avoidRepetition, setAvoidRepetition] = useDraftState(
    form,
    'avoidRepetition',
    initial?.avoid_repetition ?? true,
  );
  const [conflictId, setConflictId] = useDraftState(form, 'conflictId', initial?.conflict_id ?? '');
  const [hazard, setHazard] = useDraftState(form, 'hazard', initial?.hazard ?? '');
  const [researchArea, setResearchArea] = useDraftState<NonNullable<
    ScheduleRequest['research_area']
  > | null>(
    form,
    'researchArea',
    initial?.research_area ? { geometry: initial.research_area.geometry } : null,
  );
  const [discloseArea, setDiscloseArea] = useDraftState(
    form,
    'discloseArea',
    initial?.disclose_area_to_provider ?? false,
  );
  const [monthday, setMonthday] = useDraftState(form, 'monthday', String(initial?.monthday ?? 1));
  const [lookbackUnit, setLookbackUnit] = useDraftState<LookbackUnit>(
    form,
    'lookbackUnit',
    initial?.window_hours === null
      ? 'default'
      : initial && initial.window_hours % 24 !== 0
        ? 'hours'
        : 'days',
  );
  const [lookback, setLookback] = useDraftState(
    form,
    'lookback',
    String(
      initial?.window_hours === null
        ? 7
        : initial && initial.window_hours % 24 !== 0
          ? initial.window_hours
          : (initial?.window_hours ?? 168) / 24,
    ),
  );
  const setCadence = (value: Cadence) => {
    setLookback(lookbackForCadence(lookback, lookbackUnit, cadence, value, Boolean(initial)));
    updateCadence(value);
  };
  const changeLookbackUnit = (value: LookbackUnit) => {
    setLookback(convertLookback(lookback, lookbackUnit, value));
    setLookbackUnit(value);
  };
  const {
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
  } = evaluateSchedule(
    {
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
    },
    { templates, scope, selectedPlan, invalidPlan, initial },
  );
  const clearBoundary = () => {
    setResearchArea(null);
    setDiscloseArea(false);
  };
  const changeEventFocus = (value: { conflictId: string; hazard: string }) => {
    setConflictId(value.conflictId);
    setHazard(value.hazard);
  };
  const changeWorkspace = (teamId: string) => {
    scope.select(teamId);
    setPlanId('');
    clearBoundary();
    setSourceIds(null);
  };
  const changeSubjectFocus = (value: typeof focus) => {
    setFocus(value);
    setSubject('');
    setSourceIds(null);
  };
  const submit = (event: SyntheticEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!invalid && !busy) onSubmit(request);
  };
  return {
    scope,
    changeWorkspace,
    changeSubjectFocus,
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
    clearBoundary,
    changeEventFocus,
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

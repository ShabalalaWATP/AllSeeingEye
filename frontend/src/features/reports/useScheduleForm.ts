import { evaluateSchedule } from './scheduleDraft';
import {
  CADENCE_DAYS,
  convertLookback,
  lookbackForCadence,
  type Cadence,
  type LookbackUnit,
} from './scheduleTimingPolicy';
import { useState, type SyntheticEvent } from 'react';
import type { Category } from '@/lib/api/eventSchemas';
import type { CollectionPlan } from '@/lib/api/direction';
import type { ReportTemplate } from '@/lib/api/reports';
import type { Schedule, ScheduleRequest } from '@/lib/api/schedules';
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

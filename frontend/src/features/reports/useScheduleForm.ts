import { useState, type SyntheticEvent } from 'react';
import type { CollectionPlan } from '@/lib/api/direction';
import type { ReportTemplate } from '@/lib/api/reports';
import type { Schedule, ScheduleRequest } from '@/lib/api/schedules';
import { useWorkspaceSelection, type Workspaces } from '@/lib/hooks/useWorkspaces';
import type { Cadence, LookbackUnit } from './ScheduleTiming';

export interface ScheduleFormStateProps {
  templates: readonly ReportTemplate[];
  plans: readonly CollectionPlan[];
  workspaces: Workspaces;
  busy: boolean;
  initial?: Schedule | undefined;
  onSubmit: (request: ScheduleRequest) => void;
}

/** A schedule reuses normal research choices and evaluates its time window at each run. */
export function useScheduleForm({
  templates,
  plans,
  workspaces,
  busy,
  initial,
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
        : [],
  );
  const [question, setQuestion] = useState(initial?.question ?? '');
  const [notifyOnChange, setNotifyOnChange] = useState(initial?.notify_on_change ?? true);
  const [researchMode, setResearchMode] = useState<NonNullable<ScheduleRequest['research_mode']>>(
    initial?.research_mode ?? 'quick',
  );
  const [liveOnly, setLiveOnly] = useState(initial ? initial.research_mode === null : false);
  const [languages, setLanguages] = useState(initial?.research_languages.join(', ') ?? 'en');
  const [focus, setFocus] = useState<NonNullable<ScheduleRequest['research_focus']>>(
    initial?.research_focus ?? 'general',
  );
  const [subject, setSubject] = useState(initial?.research_subject ?? '');
  const [webSearch, setWebSearch] = useState(initial?.research_web_search ?? false);
  const [sourceIds, setSourceIds] = useState<string[] | null>(initial?.research_source_ids ?? null);
  const [chooseSources, setChooseSources] = useState(false);
  const [hour, setHour] = useState(String(initial?.hour_utc ?? 6));
  const [cadence, setCadence] = useState<Cadence>(
    (initial?.cadence as Cadence | undefined) ?? 'weekly',
  );
  const [weekday, setWeekday] = useState(String(initial?.weekday ?? 0));
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
  const activeResearch = needsQuestion && !liveOnly;
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
  const countriesInScope = subjectScoped ? [] : selectedCountries;
  const invalidQuestion =
    needsQuestion &&
    ((!question.trim() && (!selectedPlan || activeResearch)) ||
      (activeResearch && !validLanguages) ||
      (subjectScoped && !subject.trim()));
  const validWindow =
    windowHours === null ||
    (Number.isInteger(Number(lookback)) && windowHours >= 1 && windowHours <= 17520);
  const invalidCountry = product?.needs_country === true && countriesInScope.length !== 1;
  const invalid =
    !name.trim() ||
    !scope.ready ||
    !product ||
    invalidPlan ||
    invalidQuestion ||
    invalidCountry ||
    !validWindow;
  const submit = (event: SyntheticEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (invalid || busy) return;
    onSubmit({
      ...(scope.teamId ? { team_id: scope.teamId } : {}),
      ...(selectedPlan ? { plan_id: selectedPlan } : {}),
      ...(needsQuestion && question.trim() ? { question: question.trim() } : {}),
      ...(activeResearch
        ? {
            research_mode: researchMode,
            research_languages: languageCodes,
            research_subject: focus === 'general' ? null : subject.trim() || null,
            research_web_search: webSearch,
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
      research_web_search: activeResearch && webSearch,
      window_hours: windowHours,
      hour_utc: Number(hour),
      cadence,
      weekday: Number(weekday),
      monthday: Number(monthday),
    });
  };
  return {
    scope,
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
    liveOnly,
    setLiveOnly,
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
    previewLookbackDays: (windowHours ?? product?.window_hours ?? 168) / 24,
    product,
    needsQuestion,
    activeResearch,
    languageCodes,
    validLanguages,
    subjectScoped,
    countriesInScope,
    setCountries,
    invalidQuestion,
    validWindow,
    invalid,
    submit,
    setPlanId,
  };
}
export type ScheduleFormState = ReturnType<typeof useScheduleForm>;

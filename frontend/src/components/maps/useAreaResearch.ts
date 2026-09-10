import { useEffect, useRef, useState } from 'react';
import type { Profile } from '@/lib/api/profile';
import { ApiError, describeError } from '@/lib/api/errors';
import { previewResearchPlan, type ResearchPlanInput } from '@/lib/api/researchPlan';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { useResearchRun } from '@/lib/hooks/useResearchRun';
import { areasEqual } from '@/lib/map/areaGeometry';
import type { LocalCollection } from '@/lib/map/geoJsonTypes';

export const AREA_OVERVIEW_QUESTION =
  'What does the available public evidence show about this area during the selected period? ' +
  'Summarise relevant observations and developments, distinguish established facts from claims, ' +
  'and explain conflicting evidence, uncertainty and collection gaps.';
export const AREA_PERIODS = [
  { days: 1, label: 'Last 24 hours' },
  { days: 3, label: 'Last 3 days' },
  { days: 7, label: 'Last 7 days' },
  { days: 14, label: 'Last 14 days' },
] as const;
type AreaPeriod = (typeof AREA_PERIODS)[number]['days'];
type Preview = Awaited<ReturnType<typeof previewResearchPlan>>;
type AreaInput = ResearchPlanInput & {
  research_area: NonNullable<ResearchPlanInput['research_area']>;
  languages: NonNullable<ResearchPlanInput['languages']>;
};
interface CheckedArea {
  key: string;
  input: AreaInput;
  data: Preview;
}

/** A preview freezes the area, question and interval. Editing invalidates it and cancels work. */
export function useAreaResearch(
  area: LocalCollection | null,
  areaError: string | null,
  preferences: Profile | null,
) {
  const [question, setQuestion] = useState('');
  const [days, setDays] = useState<AreaPeriod>(1);
  const [mode, setMode] = useState<'quick' | 'detailed'>('detailed');
  const [checked, setChecked] = useState<CheckedArea | null>(null);
  const [approved, setApproved] = useState<CheckedArea | null>(null);
  const [pendingKey, setPendingKey] = useState<string | null>(null);
  const [failure, setFailure] = useState<{ key: string; message: string } | null>(null);
  const pending = useRef<AbortController | null>(null);
  const begin = useScopedRequest();
  const action = useResearchRun();
  const cancel = action.progress.cancel;
  const resolvedQuestion = question.trim() || AREA_OVERVIEW_QUESTION;
  const key = JSON.stringify({
    area,
    areaError,
    question: resolvedQuestion,
    days,
    mode,
    preferences,
  });
  useEffect(
    () => () => {
      pending.current?.abort();
      cancel();
    },
    [key, cancel],
  );
  const preview = checked?.key === key ? checked : null;
  const busy = pendingKey === key;
  const eligible =
    preview?.data.tasks.some((task) => task.selected && task.supported && task.spatial_supported) ??
    false;
  const consent = preview !== null && approved === preview;

  const checkSources = async () => {
    if (busy || action.busy || !preferences) return;
    if (pending.current && !pending.current.signal.aborted) return;
    if (!area || areaError || resolvedQuestion.length > 1000) {
      setFailure({
        key,
        message:
          areaError ??
          (!area
            ? 'Complete an area on the map first.'
            : 'Use a question of at most 1,000 characters.'),
      });
      return;
    }
    pending.current?.abort();
    const controller = new AbortController();
    pending.current = controller;
    const signal = AbortSignal.any([begin(), controller.signal]);
    setPendingKey(key);
    setFailure(null);
    setChecked(null);
    setApproved(null);
    const until = new Date();
    const input: AreaInput = {
      research_area: { geometry: { ...area } },
      question: resolvedQuestion,
      since: new Date(until.getTime() - days * 86_400_000).toISOString(),
      until: until.toISOString(),
      languages: preferences.research_languages,
      mode,
      focus: 'general',
      time_basis: 'acquisition_or_publication',
      source_ids: null,
      team_id: null,
    };
    try {
      const data = await previewResearchPlan(input, signal);
      if (signal.aborted) return;
      if (
        !data.area ||
        !areasEqual(area, data.area.geometry) ||
        data.map_origin !== null ||
        data.question !== input.question ||
        data.mode !== input.mode ||
        data.focus !== input.focus ||
        data.time_basis !== input.time_basis ||
        JSON.stringify(data.languages) !== JSON.stringify(input.languages) ||
        Date.parse(data.since) !== Date.parse(input.since) ||
        Date.parse(data.until) !== Date.parse(input.until)
      )
        throw new ApiError(
          422,
          'invalid_request',
          'The source preview does not match this area and research scope. Check sources again.',
        );
      setChecked({ key, input, data });
    } catch (error) {
      if (!signal.aborted) setFailure({ key, message: describeError(error) });
    } finally {
      if (pending.current === controller) {
        pending.current = null;
        setPendingKey(null);
      }
    }
  };

  const generate = async () => {
    if (!preview || !eligible || !consent || !preferences || busy || action.busy) return;
    const input = preview.input;
    await action.run({
      template: 'ask',
      question: input.question,
      research_area: input.research_area,
      research_since: input.since,
      research_until: input.until,
      research_time_basis: 'acquisition_or_publication',
      research_mode: mode,
      research_focus: 'general',
      research_languages: input.languages,
      research_source_ids: null,
      report_language: preferences.report_language,
      report_style: preferences.report_style,
      devils_advocacy: mode === 'detailed',
      team_id: null,
      disclose_area_to_provider: true,
    });
  };
  return {
    question,
    setQuestion,
    days,
    setDays,
    mode,
    setMode,
    preview: preview?.data ?? null,
    eligible,
    consent,
    setConsent: (value: boolean) => setApproved(value ? preview : null),
    busy,
    action,
    error: failure?.key === key ? failure.message : null,
    checkSources,
    generate,
  };
}

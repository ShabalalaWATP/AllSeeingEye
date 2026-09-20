import { useCallback, useState, type SyntheticEvent } from 'react';
import type { Country } from '@/lib/api/geoSchemas';
import type { Profile } from '@/lib/api/profile';
import type { ReportTemplate } from '@/lib/api/reports';
import { useWorkspaceSelection, type Workspaces } from '@/lib/hooks/useWorkspaces';
import type { ResearchDates } from '@/lib/researchPeriod';
import { projectInterval } from './ProjectHistory';
import {
  initialDraft,
  isPrivateFocus,
  researchIssue,
  researchRequest,
  type Parent,
  type ResearchDraft,
  type ResearchFocus,
} from './researchRequest';
import { changeResearchFocus } from './researchTransitions';
import { useResearchPlan } from './useResearchPlan';
import { useResearchRun } from './useResearchRun';

export function useResearchForm({
  preferences,
  workspaces,
  countries,
  countriesLoading,
  template,
  initialQuestion,
  initialDates,
  initialCountry,
  parent,
}: {
  preferences: Profile;
  workspaces: Workspaces;
  countries: readonly Country[];
  countriesLoading: boolean;
  template: ReportTemplate | undefined;
  initialQuestion: string;
  initialDates?: ResearchDates | null;
  initialCountry: string;
  parent?: Parent | undefined;
}) {
  const scope = useWorkspaceSelection(workspaces);
  const action = useResearchRun();
  const { clearError } = action;
  const [draft, setDraft] = useState<ResearchDraft>(() =>
    initialDraft(preferences, parent, initialQuestion, initialDates, initialCountry),
  );
  const patch = (changes: Partial<ResearchDraft>) =>
    setDraft((current) => ({ ...current, ...changes }));
  const [validation, setValidation] = useState<string | null>(null);
  const [inputBusy, setInputBusy] = useState(false);
  const changeInput = useCallback(
    (inputId: string | null) => {
      setDraft((current) => ({ ...current, inputId }));
      setValidation(null);
      clearError();
    },
    [clearError],
  );
  const { focus } = draft;
  const privateFocus = isPrivateFocus(focus);
  const general = focus === 'general';
  const historical = !parent && general && draft.history.enabled;
  const interval = historical ? projectInterval(draft.history) : null;
  const plan = useResearchPlan({
    ...(historical
      ? {
          history: {
            ...(interval ?? { since: '', until: '' }),
            projectId: draft.history.projectId ?? '',
          },
        }
      : {}),
    question: draft.question,
    windowHours: draft.windowHours,
    languages: draft.languages,
    mode: draft.mode,
    focus,
    subject: draft.subject,
    countries: general ? draft.countries : [],
    ...(draft.dates && !historical ? { dates: draft.dates } : {}),
    webSearch: draft.webSearch && !privateFocus,
  });
  const teamId = parent ? (parent.report.report.team_id ?? '') : scope.teamId;
  const ready = parent
    ? !workspaces.loading && (!teamId || workspaces.teams.some((entry) => entry.team.id === teamId))
    : scope.ready;
  const waiting =
    !template ||
    !ready ||
    plan.busy ||
    inputBusy ||
    (!parent && draft.countries.length > 0 && countriesLoading);
  const changeFocus = (value: ResearchFocus) =>
    setDraft((current) => changeResearchFocus(current, value));
  const submit = (event: SyntheticEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (action.busy || waiting) return;
    const ctx = { parent, countries, historical, interval, plan };
    const issue = researchIssue(draft, ctx);
    setValidation(issue);
    if (issue) return;
    void action.run(researchRequest(draft, ctx, template, scope.teamId));
  };
  return {
    scope,
    action,
    draft,
    patch,
    validation,
    setInputBusy,
    changeInput,
    focus,
    privateFocus,
    general,
    historical,
    plan,
    teamId,
    waiting,
    changeFocus,
    submit,
  };
}
export type ResearchFormProps = Parameters<typeof useResearchForm>[0];

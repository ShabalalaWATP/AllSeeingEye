import { Button } from '@/components/ui/Button';
import { SelectField, TextField } from '@/components/ui/Field';
import { WorkspaceField } from '@/components/ui/WorkspaceField';
import type { Workspaces } from '@/lib/hooks/useWorkspaces';
import type { ReportTemplate } from '@/lib/api/reports';
import { ScheduleSources } from './ScheduleSources';
import type { ScheduleFormState } from './useScheduleForm';

export function ScheduleScope({
  state,
  workspaces,
  templates,
  initial,
}: {
  state: ScheduleFormState;
  workspaces: Workspaces;
  templates: readonly ReportTemplate[];
  initial: boolean;
}) {
  const {
    scope,
    setPlanId,
    template,
    setTemplate,
    selectedPlan,
    matchingPlans,
    activeResearch,
    languages,
    setLanguages,
    validLanguages,
    focus,
    setFocus,
    setSourceIds,
    subject,
    setSubject,
    invalidQuestion,
    validWindow,
    chooseSources,
    setChooseSources,
    question,
    researchMode,
    languageCodes,
    countriesInScope,
    webSearch,
    previewLookbackDays,
    sourceIds,
  } = state;
  return (
    <details id="subscription-advanced" className="group border-t border-line pt-5">
      <summary className="cursor-pointer text-sm font-medium">Advanced scope and sources</summary>
      <div className="mt-4 space-y-4">
        <WorkspaceField
          workspaces={workspaces}
          disabled={initial}
          value={scope.teamId}
          onChange={(value) => {
            scope.select(value);
            setPlanId('');
            state.setResearchArea(null);
            state.setDiscloseArea(false);
            setSourceIds(null);
          }}
        />
        <SelectField
          label="Product"
          disabled={Boolean(state.researchArea)}
          value={template}
          onChange={(event) => setTemplate(event.target.value)}
          options={templates
            .filter((item) => !item.needs_conflict && !item.needs_hazard)
            .map((item) => ({ value: item.id, label: item.title }))}
        />
        <SelectField
          label="Collection plan"
          disabled={Boolean(activeResearch && state.researchArea)}
          value={selectedPlan}
          onChange={(event) => setPlanId(event.target.value)}
          hint="Optional. Plans must use the same workspace."
          options={[
            { value: '', label: 'No plan' },
            ...matchingPlans.map((plan) => ({ value: plan.id, label: plan.name })),
          ]}
        />
        {activeResearch && (
          <>
            <TextField
              label="Research languages"
              value={languages}
              onChange={(event) => setLanguages(event.target.value)}
              maxLength={64}
              hint="One to eight comma-separated language codes, for example en, uk."
              error={validLanguages ? undefined : 'Enter one to eight valid language codes.'}
            />
            <SelectField
              label="Research focus"
              disabled={Boolean(state.researchArea)}
              value={focus}
              onChange={(event) => {
                setFocus(event.target.value as typeof focus);
                setSubject('');
                setSourceIds(null);
              }}
              options={['general', 'company', 'domain'].map((value) => ({
                value,
                label: value.charAt(0).toUpperCase() + value.slice(1),
              }))}
            />
            {focus !== 'general' && (
              <TextField
                label="Research subject"
                value={subject}
                onChange={(event) => setSubject(event.target.value)}
                maxLength={300}
                required
                hint="Organisation name, registry identifier or domain."
              />
            )}
            <Button
              variant="secondary"
              disabled={invalidQuestion || !validWindow}
              onClick={() => setChooseSources(!chooseSources)}
            >
              {chooseSources ? 'Hide source choices' : 'Choose research sources'}
            </Button>
            {chooseSources && !invalidQuestion && validWindow && (
              <ScheduleSources
                scope={{
                  question: question.trim(),
                  mode: researchMode,
                  languages: languageCodes,
                  focus,
                  subject: focus === 'general' ? null : subject.trim() || null,
                  countries: countriesInScope,
                  research_web_search: webSearch,
                  ...(state.researchArea ? { research_area: state.researchArea } : {}),
                }}
                lookback={previewLookbackDays}
                value={sourceIds}
                onChange={setSourceIds}
              />
            )}
            {sourceIds !== null && (
              <p className="text-xs text-muted">
                {sourceIds.length} explicit source choices saved. Newly added sources are included
                only when you use all supported sources.
              </p>
            )}
          </>
        )}
      </div>
    </details>
  );
}

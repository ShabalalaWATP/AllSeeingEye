import { useState } from 'react';
import type { SyntheticEvent } from 'react';

import { WorkspaceField } from '@/components/ui/WorkspaceField';
import type { CollectionPlan } from '@/lib/api/direction';
import { useWorkspaceSelection } from '@/lib/hooks/useWorkspaces';
import type { Workspaces } from '@/lib/hooks/useWorkspaces';

import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SelectField, TextField } from '@/components/ui/Field';
import type { ReportTemplate } from '@/lib/api/reports';
import type { IndicatorRequest } from '@/lib/api/warning';
import { parseCategories, parseCommaList, parseCountries } from '@/lib/text';
import { clearAreaWatchDraft } from '@/lib/areaWatchDraft';
import type { AreaWatchDraft } from '@/lib/areaWatchDraft';
import { IndicatorAreaFields, useIndicatorArea } from './IndicatorAreaFields';

export const WINDOWS = [
  { value: '60', label: '1 hour' },
  { value: '360', label: '6 hours' },
  { value: '1440', label: '1 day' },
  { value: '10080', label: '7 days' },
];

export function describeWindow(minutes: number): string {
  if (minutes % 1440 === 0) return `${String(minutes / 1440)} d`;
  if (minutes % 60 === 0) return `${String(minutes / 60)} h`;
  return `${String(minutes)} min`;
}

interface IndicatorFormProps {
  draft?: AreaWatchDraft | null;
  templates: readonly ReportTemplate[];
  plans: readonly CollectionPlan[];
  workspaces: Workspaces;
  busy: boolean;
  error: string | null;
  onSubmit: (request: IndicatorRequest) => void;
}

/** A standing rule: what to watch, how many in what window, and what to do when it fires. */
export function IndicatorForm({
  templates,
  busy,
  error,
  onSubmit,
  plans,
  workspaces,
  draft = null,
}: IndicatorFormProps) {
  const scope = useWorkspaceSelection(workspaces);
  const [planId, setPlanId] = useState('');
  const matchingPlans = plans.filter(
    (plan) => plan.enabled && (plan.team_id ?? '') === scope.teamId,
  );
  const selectedPlan = matchingPlans.some((plan) => plan.id === planId) ? planId : '';
  const invalidPlan = planId !== '' && selectedPlan === '';
  const [name, setName] = useState('');
  const [countries, setCountries] = useState('');
  const area = useIndicatorArea(draft);
  const [keywords, setKeywords] = useState('');
  const [categories, setCategories] = useState('');
  const [threshold, setThreshold] = useState('1');
  const [window, setWindow] = useState('360');
  const [template, setTemplate] = useState('');

  const submit = (event: SyntheticEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!scope.ready || invalidPlan || area.error) return;
    onSubmit({
      ...(scope.teamId ? { team_id: scope.teamId } : {}),
      ...(selectedPlan ? { plan_id: selectedPlan } : {}),
      name: name.trim(),
      description: '',
      enabled: true,
      cooldown_minutes: 60,
      severity_floor: 0,
      countries: area.mode === 'area' ? [] : parseCountries(countries),
      ...(area.bbox ? { bbox: area.bbox } : {}),
      keywords: parseCommaList(keywords),
      categories: parseCategories(categories),
      threshold: Math.max(1, Number(threshold) || 1),
      window_minutes: Number(window),
      report_template: template === '' ? null : template,
    });
  };

  return (
    <form
      onSubmit={submit}
      aria-label="New indicator"
      className="flex flex-col gap-3 rounded-card border border-line bg-surface p-4"
    >
      {draft && (
        <div className="space-y-2 rounded border border-cyan/30 bg-cyan/5 p-3 text-sm">
          <h3 className="font-medium text-cyan">Watch this area</h3>
          <p>
            {draft.source === 'sketch-envelope'
              ? 'This approximate bounding rectangle includes areas outside your sketch. Adjust it before adding an indicator.'
              : 'Your map bounds are ready to review. Adjust the location, categories and threshold before adding an indicator.'}
          </p>
          <p className="text-xs text-muted">
            Nothing is saved yet. Reports are off by default. An indicator counts published items in
            its time window and waits 60 minutes between alerts.
          </p>
          <button
            type="button"
            className="text-xs underline"
            onClick={() => clearAreaWatchDraft(draft.id)}
          >
            Discard map draft
          </button>
        </div>
      )}
      {invalidPlan && (
        <Alert tone="error">
          The linked plan is no longer available. Choose a plan in this workspace or select No plan.
        </Alert>
      )}
      <WorkspaceField
        workspaces={workspaces}
        value={scope.teamId}
        onChange={(value) => {
          scope.select(value);
          setPlanId('');
        }}
      />
      <SelectField
        label="Collection plan"
        value={selectedPlan}
        onChange={(event) => setPlanId(event.target.value)}
        hint="Optional. Linked plans must use the same workspace."
        options={[
          { value: '', label: 'No plan' },
          ...matchingPlans.map((plan) => ({ value: plan.id, label: plan.name })),
        ]}
      />
      <IndicatorAreaFields value={area} countries={countries} onCountriesChange={setCountries} />
      <div className="grid gap-3 md:grid-cols-3">
        <TextField
          label="Indicator name"
          value={name}
          onChange={(event) => {
            setName(event.target.value);
          }}
          required
          maxLength={120}
        />
        <TextField
          label="Categories"
          hint="Comma separated, for example conflict, news."
          value={categories}
          onChange={(event) => {
            setCategories(event.target.value);
          }}
        />
        <TextField
          label="Keywords"
          hint="Any of these in a title or summary, comma separated."
          value={keywords}
          onChange={(event) => {
            setKeywords(event.target.value);
          }}
        />
        <TextField
          label="Threshold"
          hint="Fires at this many matching items in the window."
          type="number"
          min={1}
          max={10000}
          value={threshold}
          onChange={(event) => {
            setThreshold(event.target.value);
          }}
        />
        <SelectField
          label="Window"
          value={window}
          onChange={(event) => {
            setWindow(event.target.value);
          }}
          options={WINDOWS}
        />
        <SelectField
          label="Report when it fires"
          hint="Generated as you, scoped like the indicator."
          value={template}
          onChange={(event) => {
            setTemplate(event.target.value);
          }}
          options={[
            { value: '', label: 'No report' },
            ...templates.map((item) => ({ value: item.id, label: item.title })),
          ]}
        />
      </div>
      {error === null ? null : <Alert tone="error">{error}</Alert>}
      <div>
        <Button
          type="submit"
          busy={busy}
          disabled={!scope.ready || invalidPlan || area.error !== null}
        >
          Add indicator
        </Button>
      </div>
    </form>
  );
}

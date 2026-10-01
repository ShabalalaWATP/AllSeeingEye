import { useRef, useState } from 'react';
import type { SyntheticEvent } from 'react';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SelectField, TextAreaField, TextField } from '@/components/ui/Field';
import { WorkspaceField } from '@/components/ui/WorkspaceField';
import { describeError } from '@/lib/api/errors';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';
import { useWorkspaceSelection } from '@/lib/hooks/useWorkspaces';
import type { Workspaces } from '@/lib/hooks/useWorkspaces';
import { createPlan, updatePlan } from '@/lib/api/direction';
import type { AreaOfInterest, CollectionPlan } from '@/lib/api/direction';

import { PlanConflict } from './PlanConflict';
import { PlanRequirementsEditor } from './PlanRequirementsEditor';
import {
  draftFromPlan,
  emptyPlanDraft,
  PLAN_LIMITS,
  planRequest,
  validatePlanDraft,
  type PlanDraft,
  type PlanErrors,
} from './planDraft';

/** Creates a plan, or edits one in place when `plan` is given; failures keep the draft. */
export function PlanForm({
  areas,
  workspaces,
  plan,
  onSaved,
  onCancel,
}: {
  areas: readonly AreaOfInterest[];
  workspaces: Workspaces;
  plan?: CollectionPlan | undefined;
  onSaved: (saved: CollectionPlan) => Promise<void> | void;
  onCancel?: (() => void) | undefined;
}) {
  const scope = useWorkspaceSelection(workspaces);
  const teamId = plan ? (plan.team_id ?? '') : scope.teamId;
  const [draft, setDraft] = useState<PlanDraft>(() =>
    plan ? draftFromPlan(plan) : emptyPlanDraft(),
  );
  const [enabled, setEnabled] = useState(plan?.enabled ?? true);
  const [revision, setRevision] = useState(plan?.updated_at ?? '');
  const [errors, setErrors] = useState<PlanErrors>({});
  const summary = useRef<HTMLDivElement>(null);
  const matchingAreas = areas.filter((area) => (area.team_id ?? '') === teamId);
  const areaAvailable = draft.areaId === '' || matchingAreas.some((a) => a.id === draft.areaId);
  const ready = plan ? true : scope.ready;
  const change = (next: PlanDraft) => {
    setDraft(next);
    if (Object.keys(errors).length > 0) setErrors(validatePlanDraft(next, true));
  };
  const save = useAsyncAction(async (current: PlanDraft) => {
    const body = planRequest(current, teamId === '' ? null : teamId, enabled);
    if (plan) {
      const saved = await updatePlan(plan.id, { ...body, expected_updated_at: revision });
      setRevision(saved.updated_at);
      await onSaved(saved);
      return;
    }
    const saved = await createPlan(body);
    setDraft(emptyPlanDraft());
    await onSaved(saved);
  });
  const submit = (event: SyntheticEvent<HTMLFormElement>) => {
    event.preventDefault();
    const found = validatePlanDraft(draft, areaAvailable);
    setErrors(found);
    if (Object.keys(found).length > 0) {
      summary.current?.focus();
      return;
    }
    if (ready) void save.run(draft);
  };
  const conflict = plan !== undefined && save.error?.code === 'conflict';
  return (
    <form
      onSubmit={submit}
      noValidate
      aria-label={plan ? `Edit ${plan.name}` : 'New collection plan'}
      className="flex flex-col gap-3 rounded-card border border-line bg-surface p-4"
    >
      <div ref={summary} tabIndex={-1} className="outline-offset-4">
        {Object.keys(errors).length > 0 && (
          <Alert tone="error">
            Review the highlighted fields. Nothing has been saved and your draft is kept.
          </Alert>
        )}
      </div>
      {!areaAvailable && (
        <Alert tone="error">
          The linked area is no longer available. Choose an area in this workspace or select No
          area.
        </Alert>
      )}
      {matchingAreas.find((area) => area.id === draft.areaId)?.research_area && (
        <p className="text-sm text-muted">
          Exact-shape plans support evidence matching. For reports, start standalone area research
          from the saved area; collection-plan report templates cannot use this polygon.
        </p>
      )}
      {plan ? (
        <p className="text-sm text-muted">
          {workspaces.label(plan.team_id)}. A plan keeps its workspace, owner and links when edited.
        </p>
      ) : (
        <WorkspaceField
          workspaces={workspaces}
          value={scope.teamId}
          onChange={(value) => {
            scope.select(value);
            change({ ...draft, areaId: '' });
          }}
        />
      )}
      <div className="grid gap-3 md:grid-cols-3">
        <TextField
          label="Plan name"
          value={draft.name}
          error={errors.name}
          onChange={(event) => change({ ...draft, name: event.target.value })}
          required
          maxLength={PLAN_LIMITS.name}
        />
        <SelectField
          label="Area"
          hint="Optional; nations below apply when no area is chosen."
          value={areaAvailable ? draft.areaId : ''}
          onChange={(event) => change({ ...draft, areaId: event.target.value })}
          options={[
            { value: '', label: 'No area' },
            ...matchingAreas.map((area) => ({ value: area.id, label: area.name })),
          ]}
        />
        <TextField
          label="Nations"
          hint="ISO codes, comma separated."
          value={draft.countries}
          error={errors.countries}
          onChange={(event) => change({ ...draft, countries: event.target.value })}
        />
      </div>
      <PlanRequirementsEditor
        pirs={draft.pirs}
        errors={errors}
        onChange={(pirs) => change({ ...draft, pirs })}
      />
      <TextAreaField
        label="Background"
        hint="Context handed to the model with every report on this plan; never cited."
        value={draft.description}
        onChange={(event) => change({ ...draft, description: event.target.value })}
        maxLength={2000}
      />
      {plan && (
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={enabled}
            onChange={(event) => setEnabled(event.target.checked)}
          />
          Plan enabled for watchlists, map filters and new research
        </label>
      )}
      {conflict ? (
        <PlanConflict
          planId={plan.id}
          onUseLatest={(latest) => {
            setDraft(draftFromPlan(latest));
            setEnabled(latest.enabled);
            setRevision(latest.updated_at);
            setErrors({});
            save.clearError();
          }}
          onKeepMine={(latest) => {
            setRevision(latest.updated_at);
            save.clearError();
          }}
        />
      ) : save.error === null ? null : (
        <Alert tone="error">
          {describeError(save.error)} Your draft is kept; correct it or try again.
        </Alert>
      )}
      <div className="flex flex-wrap gap-2">
        <Button type="submit" busy={save.busy} disabled={!ready || conflict}>
          {plan ? 'Save plan' : 'Add plan'}
        </Button>
        {onCancel && (
          <Button variant="ghost" disabled={save.busy} onClick={onCancel}>
            Cancel editing
          </Button>
        )}
      </div>
    </form>
  );
}

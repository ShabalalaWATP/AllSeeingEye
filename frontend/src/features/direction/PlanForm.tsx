import { useState } from 'react';
import type { SyntheticEvent } from 'react';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SelectField, TextAreaField, TextField } from '@/components/ui/Field';
import { WorkspaceField } from '@/components/ui/WorkspaceField';
import { describeError } from '@/lib/api/errors';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';
import { useWorkspaceSelection } from '@/lib/hooks/useWorkspaces';
import type { Workspaces } from '@/lib/hooks/useWorkspaces';
import { createPlan } from '@/lib/api/direction';
import type { AreaOfInterest, PlanRequest } from '@/lib/api/direction';
import { parseCountries, parseSirLines } from './planText';

export function PlanForm({
  areas,
  workspaces,
  onCreated,
}: {
  areas: readonly AreaOfInterest[];
  workspaces: Workspaces;
  onCreated: () => Promise<void>;
}) {
  const scope = useWorkspaceSelection(workspaces);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [areaId, setAreaId] = useState('');
  const [countries, setCountries] = useState('');
  const [pir, setPir] = useState('');
  const [sirs, setSirs] = useState('');
  const matchingAreas = areas.filter((area) => (area.team_id ?? '') === scope.teamId);
  const selectedArea = matchingAreas.some((area) => area.id === areaId) ? areaId : '';
  const invalidArea = areaId !== '' && selectedArea === '';
  const create = useAsyncAction(async (request: PlanRequest) => {
    await createPlan(request);
    setName('');
    setDescription('');
    setPir('');
    setSirs('');
    await onCreated();
  });
  const submit = (event: SyntheticEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!scope.ready || invalidArea) return;
    const request: PlanRequest = {
      name: name.trim(),
      enabled: true,
      ...(scope.teamId ? { team_id: scope.teamId } : {}),
      description: description.trim(),
      aoi_id: selectedArea === '' ? null : selectedArea,
      countries: parseCountries(countries),
      pirs: [{ text: pir.trim(), sirs: parseSirLines(sirs) }],
    };
    void create.run(request);
  };
  return (
    <form
      onSubmit={submit}
      aria-label="New collection plan"
      className="flex flex-col gap-3 rounded-card border border-line bg-surface p-4"
    >
      {invalidArea && (
        <Alert tone="error">
          The linked area is no longer available. Choose an area in this workspace or select No
          area.
        </Alert>
      )}
      <WorkspaceField
        workspaces={workspaces}
        value={scope.teamId}
        onChange={(value) => {
          scope.select(value);
          setAreaId('');
        }}
      />
      <div className="grid gap-3 md:grid-cols-3">
        <TextField
          label="Plan name"
          value={name}
          onChange={(event) => {
            setName(event.target.value);
          }}
          required
          maxLength={120}
        />
        <SelectField
          label="Area"
          hint="Optional; nations below apply when no area is chosen."
          value={selectedArea}
          onChange={(event) => {
            setAreaId(event.target.value);
          }}
          options={[
            { value: '', label: 'No area' },
            ...matchingAreas.map((area) => ({ value: area.id, label: area.name })),
          ]}
        />
        <TextField
          label="Nations"
          hint="ISO codes, comma separated."
          value={countries}
          onChange={(event) => {
            setCountries(event.target.value);
          }}
        />
      </div>
      <TextField
        label="Priority intelligence requirement"
        hint="The question the plan serves, as one sentence."
        value={pir}
        onChange={(event) => {
          setPir(event.target.value);
        }}
        required
        maxLength={300}
      />
      <TextAreaField
        label="Specific requirements"
        hint="One per line: text | keywords, comma separated | categories, comma separated"
        value={sirs}
        onChange={(event) => {
          setSirs(event.target.value);
        }}
        required
      />
      <TextAreaField
        label="Background"
        hint="Context handed to the model with every report on this plan; never cited."
        value={description}
        onChange={(event) => {
          setDescription(event.target.value);
        }}
        maxLength={2000}
      />
      {create.error === null ? null : <Alert tone="error">{describeError(create.error)}</Alert>}
      <div>
        <Button type="submit" busy={create.busy} disabled={!scope.ready || invalidArea}>
          Add plan
        </Button>
      </div>
    </form>
  );
}

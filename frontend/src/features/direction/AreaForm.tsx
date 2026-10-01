import { useState } from 'react';
import type { SyntheticEvent } from 'react';
import { Button } from '@/components/ui/Button';
import { SelectField, TextField } from '@/components/ui/Field';
import { WorkspaceField } from '@/components/ui/WorkspaceField';
import { FormErrors } from '@/components/ui/FormErrors';
import { useFieldErrors } from '@/lib/api/fieldErrors';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';
import { useWorkspaceSelection } from '@/lib/hooks/useWorkspaces';
import type { Workspaces } from '@/lib/hooks/useWorkspaces';
import { createAoi } from '@/lib/api/direction';
import type { AoiRequest } from '@/lib/api/direction';
import { parseBox, parseCountries } from './planText';

/** Form fields for the API paths an area request can reject. */
const AREA_FIELDS = {
  team_id: 'Workspace',
  name: 'Area name',
  kind: 'Kind',
  bbox: 'West, south, east, north',
  countries: 'Nations',
} as const;

export function AreaForm({
  onCreated,
  workspaces,
}: {
  onCreated: () => Promise<void>;
  workspaces: Workspaces;
}) {
  const scope = useWorkspaceSelection(workspaces);
  const [name, setName] = useState('');
  const [kind, setKind] = useState<'bbox' | 'countries'>('bbox');
  const [box, setBox] = useState('');
  const [countries, setCountries] = useState('');
  const create = useAsyncAction(async (request: AoiRequest) => {
    await createAoi(request);
    setName('');
    setBox('');
    setCountries('');
    await onCreated();
  });
  const errors = useFieldErrors(create.error, AREA_FIELDS);
  const submit = (event: SyntheticEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!scope.ready) return;
    const request: AoiRequest = {
      name: name.trim(),
      description: '',
      kind,
      ...(scope.teamId ? { team_id: scope.teamId } : {}),
    };
    if (kind === 'bbox') {
      const parsed = parseBox(box);
      if (parsed !== null) request.bbox = parsed;
    } else {
      request.countries = parseCountries(countries);
    }
    void create.run(request);
  };
  return (
    <form
      onSubmit={submit}
      aria-label="New area of interest"
      className="flex flex-col gap-3 rounded-card border border-line bg-surface p-4"
    >
      <div id={errors.id('team_id')}>
        <WorkspaceField workspaces={workspaces} value={scope.teamId} onChange={scope.select} />
      </div>
      <div className="grid gap-3 md:grid-cols-3">
        <TextField
          label="Area name"
          {...errors.field('name')}
          value={name}
          onChange={(event) => {
            setName(event.target.value);
          }}
          required
          maxLength={120}
        />
        <SelectField
          label="Kind"
          {...errors.field('kind')}
          value={kind}
          onChange={(event) => {
            setKind(event.target.value === 'countries' ? 'countries' : 'bbox');
          }}
          options={[
            { value: 'bbox', label: 'Bounding box' },
            { value: 'countries', label: 'Nations' },
          ]}
        />
        {kind === 'bbox' ? (
          <TextField
            label="West, south, east, north"
            {...errors.field('bbox')}
            hint="Degrees, comma separated."
            value={box}
            onChange={(event) => {
              setBox(event.target.value);
            }}
            required
          />
        ) : (
          <TextField
            label="Nations"
            {...errors.field('countries')}
            hint="ISO codes, comma separated."
            value={countries}
            onChange={(event) => {
              setCountries(event.target.value);
            }}
            required
          />
        )}
      </div>
      <FormErrors errors={errors} />
      <div>
        <Button type="submit" busy={create.busy} disabled={!scope.ready}>
          Add area
        </Button>
      </div>
    </form>
  );
}

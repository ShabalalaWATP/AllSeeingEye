import { useState } from 'react';
import type { SyntheticEvent } from 'react';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SelectField, TextField } from '@/components/ui/Field';
import { WorkspaceField } from '@/components/ui/WorkspaceField';
import { describeError } from '@/lib/api/errors';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';
import { useWorkspaceSelection } from '@/lib/hooks/useWorkspaces';
import type { Workspaces } from '@/lib/hooks/useWorkspaces';
import { createAoi } from '@/lib/api/direction';
import type { AoiRequest } from '@/lib/api/direction';
import { parseBox, parseCountries } from './planText';

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
      <WorkspaceField workspaces={workspaces} value={scope.teamId} onChange={scope.select} />
      <div className="grid gap-3 md:grid-cols-3">
        <TextField
          label="Area name"
          value={name}
          onChange={(event) => {
            setName(event.target.value);
          }}
          required
          maxLength={120}
        />
        <SelectField
          label="Kind"
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
            hint="ISO codes, comma separated."
            value={countries}
            onChange={(event) => {
              setCountries(event.target.value);
            }}
            required
          />
        )}
      </div>
      {create.error === null ? null : <Alert tone="error">{describeError(create.error)}</Alert>}
      <div>
        <Button type="submit" busy={create.busy} disabled={!scope.ready}>
          Add area
        </Button>
      </div>
    </form>
  );
}

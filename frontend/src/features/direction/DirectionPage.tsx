import { useCallback, useState } from 'react';
import type { SyntheticEvent } from 'react';
import { Link } from 'react-router';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SelectField, TextAreaField, TextField } from '@/components/ui/Field';
import { Table, Td, Th } from '@/components/ui/Table';
import { createAoi, createPlan, deleteAoi, fetchAois, fetchPlans } from '@/lib/api/direction';
import type { AoiRequest, AreaOfInterest, PlanRequest } from '@/lib/api/direction';
import { describeError } from '@/lib/api/errors';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';
import { useResource } from '@/lib/hooks/useResource';

import { parseBox, parseCountries, parseSirLines } from './planText';

export function describeArea(area: AreaOfInterest): string {
  if (area.kind === 'bbox' && area.bbox !== null) {
    return `box ${area.bbox.map((n) => n.toFixed(1)).join(', ')}`;
  }
  return `nations ${area.countries.join(', ')}`;
}

function AreaForm({ onCreated }: { onCreated: () => Promise<void> }) {
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
    const request: AoiRequest = { name: name.trim(), kind };
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
        <Button type="submit" busy={create.busy}>
          Add area
        </Button>
      </div>
    </form>
  );
}

function PlanForm({
  areas,
  onCreated,
}: {
  areas: readonly AreaOfInterest[];
  onCreated: () => Promise<void>;
}) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [areaId, setAreaId] = useState('');
  const [countries, setCountries] = useState('');
  const [pir, setPir] = useState('');
  const [sirs, setSirs] = useState('');
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
    const request: PlanRequest = {
      name: name.trim(),
      description: description.trim(),
      aoi_id: areaId === '' ? null : areaId,
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
          value={areaId}
          onChange={(event) => {
            setAreaId(event.target.value);
          }}
          options={[
            { value: '', label: 'No area' },
            ...areas.map((area) => ({ value: area.id, label: area.name })),
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
        <Button type="submit" busy={create.busy}>
          Add plan
        </Button>
      </div>
    </form>
  );
}

export default function DirectionPage() {
  const areas = useResource(fetchAois);
  const plans = useResource(fetchPlans);
  const reloadAreas = areas.reload;
  const reloadPlans = plans.reload;
  const remove = useAsyncAction(
    useCallback(
      async (id: string) => {
        await deleteAoi(id);
        await reloadAreas();
      },
      [reloadAreas],
    ),
  );
  return (
    <section className="flex h-full flex-col gap-6 overflow-y-auto p-6">
      <h1 className="text-xl font-semibold">Direction</h1>
      <p className="text-sm text-muted">
        Areas of interest scope the picture; collection plans turn a question into requirements
        the Eye gathers evidence against and answers on demand.
      </p>
      <div className="flex flex-col gap-3">
        <h2 className="text-base font-semibold">Areas of interest</h2>
        {areas.error === null ? null : <Alert tone="error">{describeError(areas.error)}</Alert>}
        {remove.error === null ? null : <Alert tone="error">{describeError(remove.error)}</Alert>}
        {areas.data === null ? (
          areas.loading ? (
            <LoadingNote label="Loading areas" />
          ) : null
        ) : areas.data.length === 0 ? (
          <p className="text-sm text-muted">No areas yet.</p>
        ) : (
          <Table caption="Areas of interest">
            <thead>
              <tr>
                <Th>Area</Th>
                <Th>Extent</Th>
                <Th />
              </tr>
            </thead>
            <tbody>
              {areas.data.map((area) => (
                <tr key={area.id}>
                  <Td className="font-medium">{area.name}</Td>
                  <Td className="font-mono text-xs text-muted">{describeArea(area)}</Td>
                  <Td>
                    <Button
                      variant="danger"
                      busy={remove.busy}
                      onClick={() => void remove.run(area.id)}
                    >
                      Delete
                    </Button>
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
        <AreaForm onCreated={reloadAreas} />
      </div>
      <div className="flex flex-col gap-3">
        <h2 className="text-base font-semibold">Collection plans</h2>
        {plans.error === null ? null : <Alert tone="error">{describeError(plans.error)}</Alert>}
        {plans.data === null ? (
          plans.loading ? (
            <LoadingNote label="Loading plans" />
          ) : null
        ) : plans.data.length === 0 ? (
          <p className="text-sm text-muted">No plans yet.</p>
        ) : (
          <ul aria-label="Collection plans" className="flex flex-col gap-2">
            {plans.data.map((plan) => (
              <li key={plan.id} className="rounded-card border border-line bg-surface p-3">
                <Link
                  to={`/direction/plans/${plan.id}`}
                  className="font-medium text-text hover:underline"
                >
                  {plan.name}
                </Link>
                <p className="mt-1 text-xs text-muted">
                  {plan.pirs.length} PIR, {plan.pirs.reduce((n, pir) => n + pir.sirs.length, 0)}{' '}
                  SIR{plan.countries.length > 0 ? ` · ${plan.countries.join(', ')}` : ''}
                </p>
              </li>
            ))}
          </ul>
        )}
        <PlanForm areas={areas.data ?? []} onCreated={reloadPlans} />
      </div>
    </section>
  );
}

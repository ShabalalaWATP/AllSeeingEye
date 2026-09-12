import { useState } from 'react';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SelectField } from '@/components/ui/Field';
import { fetchAois } from '@/lib/api/direction';
import { describeError } from '@/lib/api/errors';
import { fetchConflictBoard, fetchDisasterBoard } from '@/lib/api/trackers';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { rectangleArea } from '@/lib/map/areaGeometry';
import type { ScheduleFormState } from './useScheduleForm';

async function loadCoverage() {
  const [areas, conflicts, hazards] = await Promise.all([
    fetchAois(),
    fetchConflictBoard(),
    fetchDisasterBoard(),
  ]);
  return { areas, conflicts, hazards };
}

export function SubscriptionCoverage({ state }: { state: ScheduleFormState }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border-t border-line pt-4">
      <Button variant="secondary" aria-expanded={open} onClick={() => setOpen(!open)}>
        {open ? 'Hide topic and area filters' : 'Choose a conflict, disaster or saved area'}
      </Button>
      {(state.conflictId || state.hazard || state.researchArea) && (
        <p className="mt-2 text-xs text-muted">Saved topic or area filters apply to every run.</p>
      )}
      {open && <CoverageFields state={state} />}
    </div>
  );
}

function CoverageFields({ state }: { state: ScheduleFormState }) {
  const choices = useScopedResource(loadCoverage);
  const [areaId, setAreaId] = useState('');
  const [areaError, setAreaError] = useState<string | null>(null);
  const areas =
    choices.data?.areas.filter((area) => (area.team_id ?? '') === state.scope.teamId) ?? [];
  const oversizedAreas = areas.filter((area) => !area.bbox && area.countries.length > 8);
  const clearBoundary = () => {
    setAreaError(null);
    state.setResearchArea(null);
    state.setDiscloseArea(false);
    setAreaId('');
  };
  return (
    <div className="mt-4 space-y-4">
      <p className="text-xs text-muted">
        Follow any theme in your question, or narrow it to a conflict, disaster or fixed area. Exact
        boundaries replace country, topic and collection-plan filters.
      </p>
      {choices.loading && <LoadingNote label="Loading topic and area choices" />}
      {choices.error && (
        <Alert tone="error">
          {describeError(choices.error)}{' '}
          <Button variant="secondary" onClick={() => void choices.reload()}>
            Retry choices
          </Button>
        </Alert>
      )}
      {choices.data && (
        <>
          <SelectField
            label="Conflict"
            value={state.conflictId}
            onChange={(event) => {
              state.setConflictId(event.target.value);
              state.setHazard('');
              clearBoundary();
            }}
            options={[
              { value: '', label: 'No conflict filter' },
              ...choices.data.conflicts.map(({ conflict }) => ({
                value: conflict.id,
                label: conflict.name,
              })),
              ...(state.conflictId &&
              !choices.data.conflicts.some(({ conflict }) => conflict.id === state.conflictId)
                ? [{ value: state.conflictId, label: `Saved conflict: ${state.conflictId}` }]
                : []),
            ]}
          />
          <SelectField
            label="Natural disaster"
            value={state.hazard}
            onChange={(event) => {
              state.setHazard(event.target.value);
              state.setConflictId('');
              clearBoundary();
            }}
            options={[
              { value: '', label: 'No disaster filter' },
              ...choices.data.hazards.map(({ hazard, title }) => ({ value: hazard, label: title })),
              ...(state.hazard &&
              !choices.data.hazards.some(({ hazard }) => hazard === state.hazard)
                ? [{ value: state.hazard, label: `Saved disaster: ${state.hazard}` }]
                : []),
            ]}
          />
          {state.activeResearch && (
            <>
              <SelectField
                label="Saved area"
                value={areaId}
                hint="Areas use the same saved boundaries as Plans & areas. A copy is saved to this subscription; later area edits do not change it."
                onChange={(event) => {
                  const id = event.target.value;
                  clearBoundary();
                  setAreaId(id);
                  const area = areas.find((item) => item.id === id);
                  if (!area || (!area.bbox && area.countries.length > 8)) return;
                  state.setConflictId('');
                  state.setHazard('');
                  state.setPlanId('');
                  if (area.bbox?.length === 4) {
                    const [west, south, east, north] = area.bbox;
                    state.setCountries([]);
                    state.setSourceIds(null);
                    try {
                      state.setResearchArea({
                        geometry: {
                          ...rectangleArea({
                            west: west ?? NaN,
                            south: south ?? NaN,
                            east: east ?? NaN,
                            north: north ?? NaN,
                          }),
                        },
                      });
                    } catch {
                      setAreaError(
                        'This saved area has invalid bounds. Choose another area or correct it in Plans & areas.',
                      );
                    }
                  } else state.setCountries(area.countries);
                }}
                options={[
                  {
                    value: '',
                    label: state.researchArea ? 'Saved boundary (kept)' : 'No boundary filter',
                  },
                  ...areas
                    .filter((area) => area.bbox !== null || area.countries.length <= 8)
                    .map((area) => ({ value: area.id, label: area.name })),
                ]}
              />
              {areaError && <Alert tone="error">{areaError}</Alert>}
              {oversizedAreas.length > 0 && (
                <p className="text-xs text-muted">
                  Subscriptions support up to eight countries. These saved areas exceed that limit:{' '}
                  {oversizedAreas.map((area) => area.name).join(', ')}. Choose a smaller area or a
                  fixed boundary.
                </p>
              )}
              {areas.length === 0 && (
                <p className="text-xs text-muted">
                  Create an area in Plans & areas to reuse it here. Country filters work without a
                  saved area.
                </p>
              )}
              {state.researchArea && (
                <>
                  <div className="flex items-center justify-between gap-3 text-xs text-muted">
                    <span>A fixed geographic boundary is saved for each run.</span>
                    <Button variant="ghost" onClick={clearBoundary}>
                      Clear boundary
                    </Button>
                  </div>
                  <label className="flex items-start gap-3 text-sm">
                    <input
                      type="checkbox"
                      className="mt-1 h-4 w-4 accent-ember"
                      checked={state.discloseArea}
                      onChange={(event) => state.setDiscloseArea(event.target.checked)}
                    />
                    <span>
                      Allow source providers to receive this area
                      <span className="mt-1 block text-xs text-muted">
                        Required before an area subscription can run. Each run shares this boundary
                        and the search interval with selected providers.
                      </span>
                    </span>
                  </label>
                </>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}

/**
 * Narrow a subscription to one conflict or one natural disaster. The choices come from the
 * trackers, so a name here is a name the boards already know. A boundary drawn on the map
 * can also arrive with the subscription; it is shown, never edited here.
 */
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SelectField } from '@/components/ui/Field';
import { describeError } from '@/lib/api/errors';
import { fetchConflictBoard, fetchDisasterBoard } from '@/lib/api/trackers';
import { useScopedResource } from '@/lib/hooks/useScopedResource';

import type { ScheduleFormState } from './useScheduleForm';

async function loadFocus() {
  const [conflicts, hazards] = await Promise.all([fetchConflictBoard(), fetchDisasterBoard()]);
  return { conflicts, hazards };
}

export function ScheduleFocus({ state }: { state: ScheduleFormState }) {
  const choices = useScopedResource(loadFocus);
  const clearBoundary = () => {
    state.setResearchArea(null);
    state.setDiscloseArea(false);
  };
  return (
    <div className="space-y-4">
      {choices.loading && !choices.data && <LoadingNote label="Loading conflicts and disasters" />}
      {choices.error && (
        <Alert tone="error">
          {describeError(choices.error)}{' '}
          <Button variant="secondary" onClick={() => void choices.reload()}>
            Retry choices
          </Button>
        </Alert>
      )}
      {choices.data && (
        <div className="grid gap-4 sm:grid-cols-2">
          <SelectField
            label="Conflict"
            hint="Follow one tracked conflict. Its countries join the scope."
            value={state.conflictId}
            disabled={Boolean(state.researchArea)}
            onChange={(event) => {
              state.setConflictId(event.target.value);
              state.setHazard('');
            }}
            options={[
              { value: '', label: 'Any or none' },
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
            hint="Follow one kind of hazard wherever it is reported."
            value={state.hazard}
            disabled={Boolean(state.researchArea)}
            onChange={(event) => {
              state.setHazard(event.target.value);
              state.setConflictId('');
            }}
            options={[
              { value: '', label: 'Any or none' },
              ...choices.data.hazards.map(({ hazard, title }) => ({ value: hazard, label: title })),
              ...(state.hazard &&
              !choices.data.hazards.some(({ hazard }) => hazard === state.hazard)
                ? [{ value: state.hazard, label: `Saved disaster: ${state.hazard}` }]
                : []),
            ]}
          />
        </div>
      )}
      {state.researchArea && (
        <div className="space-y-3 rounded-xl border border-ember/30 bg-ember/5 p-4">
          <div className="flex items-center justify-between gap-3 text-sm">
            <span>
              A boundary drawn on the map is saved with this subscription and searched each run.
            </span>
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
                Required before an area subscription can run. Each run shares this boundary and the
                search interval with selected providers.
              </span>
            </span>
          </label>
        </div>
      )}
    </div>
  );
}

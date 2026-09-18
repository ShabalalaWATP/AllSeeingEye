/**
 * Narrow a subscription to one conflict or one natural disaster. A boundary drawn on the
 * map can also arrive with the subscription; it is shown, never edited here.
 */
import { FocusPicker } from '@/components/research/FocusPicker';
import { Button } from '@/components/ui/Button';

import type { ScheduleFormState } from './useScheduleForm';

export function ScheduleFocus({ state }: { state: ScheduleFormState }) {
  const clearBoundary = () => {
    state.setResearchArea(null);
    state.setDiscloseArea(false);
  };
  return (
    <div className="space-y-4">
      <FocusPicker
        conflictId={state.conflictId}
        hazard={state.hazard}
        disabled={Boolean(state.researchArea)}
        onChange={({ conflictId, hazard }) => {
          state.setConflictId(conflictId);
          state.setHazard(hazard);
        }}
      />
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

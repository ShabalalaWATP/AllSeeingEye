/**
 * Narrow a subscription to one conflict or one natural disaster. A boundary drawn on the
 * map can also arrive with the subscription; it is shown, never edited here.
 */
import { FocusPicker } from '@/components/research/FocusPicker';
import { Button } from '@/components/ui/Button';

interface ScheduleFocusProps {
  conflictId: string;
  hazard: string;
  hasBoundary: boolean;
  discloseArea: boolean;
  onEventFocus: (value: { conflictId: string; hazard: string }) => void;
  onClearBoundary: () => void;
  onDiscloseArea: (value: boolean) => void;
}

export function ScheduleFocus({
  conflictId,
  hazard,
  hasBoundary,
  discloseArea,
  onEventFocus,
  onClearBoundary,
  onDiscloseArea,
}: ScheduleFocusProps) {
  return (
    <div className="space-y-4">
      <FocusPicker
        conflictId={conflictId}
        hazard={hazard}
        disabled={hasBoundary}
        onChange={onEventFocus}
      />
      {hasBoundary && (
        <div className="space-y-3 rounded-xl border border-ember/30 bg-ember/5 p-4">
          <div className="flex items-center justify-between gap-3 text-sm">
            <span>
              A boundary drawn on the map is saved with this subscription and searched each run.
            </span>
            <Button variant="ghost" onClick={onClearBoundary}>
              Clear boundary
            </Button>
          </div>
          <label className="flex items-start gap-3 text-sm">
            <input
              type="checkbox"
              className="mt-1 h-4 w-4 accent-ember"
              checked={discloseArea}
              onChange={(event) => onDiscloseArea(event.target.checked)}
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

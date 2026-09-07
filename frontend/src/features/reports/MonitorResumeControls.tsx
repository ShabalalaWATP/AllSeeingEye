import { useState } from 'react';
import { Button } from '@/components/ui/Button';

export function MonitorResumeControls({
  busy,
  onCatchUp,
  onFreshBaseline,
}: {
  busy: boolean;
  onCatchUp: () => void;
  onFreshBaseline: () => void;
}) {
  const [confirm, setConfirm] = useState(false);
  return (
    <section aria-label="Resume monitoring" className="space-y-3 border-t border-line pt-4">
      <h3 className="font-medium">Resume monitoring</h3>
      <p className="text-sm text-muted">
        Catch up keeps the retained checkpoint. Changes recorded while paused will be processed and
        may generate alerts under the retained notification policy.
      </p>
      <Button disabled={busy} onClick={onCatchUp}>
        Resume and catch up
      </Button>
      <div className="space-y-3 rounded border border-line p-3">
        <p className="text-sm text-muted">
          A fresh baseline deliberately skips pending differences without retrospective alerts.
          Existing transition history is retained.
        </p>
        <label className="flex items-start gap-2 text-sm">
          <input
            type="checkbox"
            checked={confirm}
            disabled={busy}
            onChange={(event) => setConfirm(event.target.checked)}
          />
          I want to skip pending differences and start a fresh baseline.
        </label>
        <Button variant="secondary" disabled={busy || !confirm} onClick={onFreshBaseline}>
          Confirm fresh baseline and resume
        </Button>
      </div>
    </section>
  );
}

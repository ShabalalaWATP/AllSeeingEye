import { useState } from 'react';
import { Button } from '@/components/ui/Button';
export function MonitorRemoval({ busy, onRemove }: { busy: boolean; onRemove: () => void }) {
  const [open, setOpen] = useState(false);
  const [confirm, setConfirm] = useState(false);
  return (
    <section className="space-y-3 border-t border-line pt-4">
      <Button variant="secondary" disabled={busy} onClick={() => setOpen(true)}>
        Remove monitor and history
      </Button>
      {open && (
        <div className="space-y-3 rounded border border-critical/50 p-3">
          <p className="text-sm">
            Permanent removal deletes this monitor, its retained transitions, queued observations
            and monitor alerts. The report and other monitors are preserved. This cannot be undone.
          </p>
          <label className="flex gap-2 text-sm">
            <input
              type="checkbox"
              checked={confirm}
              disabled={busy}
              onChange={(event) => setConfirm(event.target.checked)}
            />
            I understand this monitor and its history will be permanently removed.
          </label>
          <div className="flex gap-3">
            <Button disabled={busy || !confirm} onClick={onRemove}>
              Permanently remove monitor
            </Button>
            <Button
              variant="secondary"
              disabled={busy}
              onClick={() => {
                setOpen(false);
                setConfirm(false);
              }}
            >
              Cancel removal
            </Button>
          </div>
        </div>
      )}
    </section>
  );
}

import { useState } from 'react';

import { Button } from '@/components/ui/Button';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';

/**
 * Regenerate and delete for a saved report. Deletion is confirmed first, naming the report,
 * its workspace and everything the server removes with it. The page owns the request, so a
 * failure (including a refusal) stays in the confirmation beside a retry; on success the
 * page leaves the deleted report.
 */
export function ReportManagement({
  title,
  workspaceLabel,
  versions,
  actionError,
  regenerating,
  deleting,
  onRegenerate,
  onDelete,
}: {
  title: string;
  workspaceLabel: string;
  versions: number;
  actionError: string | null;
  regenerating: boolean;
  deleting: boolean;
  onRegenerate: () => void;
  onDelete: () => void;
}) {
  const [confirming, setConfirming] = useState(false);
  // Only an error from a deletion attempted in this confirmation belongs inside it.
  const [attempted, setAttempted] = useState(false);
  const close = () => {
    setConfirming(false);
    setAttempted(false);
  };
  return (
    <section aria-label="Report management" className="border-b border-line pb-6">
      <h2 className="text-base font-semibold">Report management</h2>
      <p className="mt-1 text-xs leading-5 text-muted">
        Regeneration creates a new version. Deleting removes the saved report and every version.
      </p>
      <div className="mt-3 flex gap-2">
        <Button
          variant="secondary"
          busy={regenerating}
          busyLabel="Regenerating…"
          disabled={deleting}
          onClick={onRegenerate}
        >
          Regenerate
        </Button>
        <Button
          variant="danger"
          disabled={regenerating}
          aria-haspopup="dialog"
          onClick={() => setConfirming(true)}
        >
          Delete report
        </Button>
      </div>
      <ConfirmDialog
        open={confirming}
        title={`Delete report “${title}”?`}
        confirmLabel="Delete report"
        busyLabel="Deleting report…"
        busy={deleting}
        error={attempted && !deleting ? actionError : null}
        onCancel={close}
        onConfirm={() => {
          setAttempted(true);
          onDelete();
        }}
      >
        <p>
          <span className="font-medium text-text">Workspace:</span> {workspaceLabel}
        </p>
        <p>
          This permanently deletes the report,{' '}
          {versions === 1 ? 'its saved version' : `all ${versions} saved versions`} and the frozen
          evidence kept with them, including claims, reviews, original assets, saved maps and
          annotation monitors. Files you have already exported are not affected.
        </p>
        <p className="font-medium text-critical">This cannot be undone.</p>
      </ConfirmDialog>
    </section>
  );
}

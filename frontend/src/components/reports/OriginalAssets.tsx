import { useCallback, useState } from 'react';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import type { EvidenceItem } from '@/lib/api/reports';
import {
  listOriginalAssets,
  downloadOriginalAsset,
  deleteOriginalAsset,
} from '@/lib/api/originalAssets';
import type { OriginalAsset } from '@/lib/api/originalAssets';
import { describeError } from '@/lib/api/errors';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { formatUtc } from '@/lib/format';
import { saveBinaryFile } from '@/lib/downloadBinary';
import { OriginalAssetForm } from './OriginalAssetForm';
import { OriginalAssetExportChoice, useOriginalAssetSelection } from './ClaimExportSelection';

function AssetRow({
  value,
  canEdit,
  reload,
}: {
  value: OriginalAsset;
  canEdit: boolean;
  reload: () => void;
}) {
  const request = useScopedRequest();
  const selection = useOriginalAssetSelection();
  const [busy, setBusy] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const active = value.status === 'active';
  const run = async (remove: boolean) => {
    const signal = request();
    setBusy(true);
    setError(null);
    try {
      if (remove) {
        await deleteOriginalAsset(value.report_id, value.id, signal);
        if (!signal.aborted) {
          selection?.removeAsset(value.id);
          reload();
        }
      } else {
        const blob = await downloadOriginalAsset(value.report_id, value.id, signal);
        if (!signal.aborted) saveBinaryFile(`original-${value.id}.bin`, blob);
      }
    } catch (caught) {
      if (!signal.aborted) setError(caught);
    } finally {
      if (!signal.aborted) setBusy(false);
    }
  };
  return (
    <li className="space-y-2 rounded border border-line p-4 [overflow-wrap:anywhere]">
      <p className="font-medium">
        {value.evidence_label} · {value.filename}
      </p>
      <p className="text-xs text-muted">
        {value.status} · {(value.byte_count / 1024).toFixed(1)} KiB · {value.media_type} · Expires{' '}
        {formatUtc(value.expires_at)}
      </p>
      <p className="font-mono text-xs">Original SHA-256: {value.sha256}</p>
      <p className="text-sm">Permitted-use declaration: {value.permitted_use}</p>
      {active && (
        <>
          <p className="text-xs text-muted">
            Bytes match the frozen original hash. This does not establish authenticity or accuracy.
          </p>
          <OriginalAssetExportChoice value={value} />
        </>
      )}
      <div className="flex flex-wrap gap-2">
        {active && (
          <Button variant="secondary" disabled={busy} onClick={() => void run(false)}>
            Download original
          </Button>
        )}
        {canEdit && !confirmDelete && (
          <Button
            variant="secondary"
            disabled={busy || selection?.busy}
            onClick={() => setConfirmDelete(true)}
          >
            Delete retained original
          </Button>
        )}
        {canEdit && confirmDelete && (
          <>
            <p className="w-full text-sm">
              Delete these retained bytes? This cannot be undone. The frozen report stays available.
            </p>
            <Button
              variant="danger"
              disabled={busy || selection?.busy}
              onClick={() => void run(true)}
            >
              Confirm deletion
            </Button>
            <Button variant="secondary" disabled={busy} onClick={() => setConfirmDelete(false)}>
              Keep original
            </Button>
          </>
        )}
      </div>
      {error !== null && <Alert tone="error">{describeError(error)}</Alert>}
    </li>
  );
}

export function OriginalAssets({
  reportId,
  version,
  evidence,
  canEdit,
}: {
  reportId: string;
  version: number;
  evidence: EvidenceItem[];
  canEdit: boolean;
}) {
  const request = useScopedRequest();
  const loader = useCallback(
    () => listOriginalAssets(reportId, version, request()),
    [reportId, version, request],
  );
  const resource = useScopedResource(loader);
  return (
    <section aria-label="Retained original evidence" className="mt-4 space-y-4">
      <h3 className="font-medium">Retained original evidence · Version {version}</h3>
      <p className="text-sm text-muted">
        Deliberately preserve an imported source file for this exact report version. Original files
        are shared with readers of this report. No web pages are captured automatically.
      </p>
      <p className="text-xs text-muted">
        Storage limits, including reservations and retained deletion records: personal 64 records /
        64 MiB; team 256 records / 256 MiB; service 4,096 records / 1 GiB. At most two uploads can
        be reserved across the service. Deletion frees bytes immediately; its record allowance
        resets after 30 days.
      </p>
      {resource.loading && <LoadingNote label="Loading retained originals" />}
      {resource.error && <Alert tone="error">{describeError(resource.error)}</Alert>}
      <Button variant="secondary" onClick={() => void resource.reload()}>
        Refresh originals
      </Button>
      {resource.data?.items.length === 0 && (
        <p className="text-sm text-muted">No originals retained for this version.</p>
      )}
      {resource.data && (
        <ul className="space-y-3">
          {resource.data.items.map((item) => (
            <AssetRow
              key={item.id}
              value={item}
              canEdit={canEdit}
              reload={() => void resource.reload()}
            />
          ))}
        </ul>
      )}
      {canEdit ? (
        <OriginalAssetForm
          key={`${resource.key}:${reportId}:${String(version)}`}
          reportId={reportId}
          version={version}
          evidence={evidence}
          onSaved={() => void resource.reload()}
        />
      ) : (
        <p className="text-sm text-muted">
          You have read access. A report owner, team manager or administrator can retain and delete
          originals.
        </p>
      )}
    </section>
  );
}

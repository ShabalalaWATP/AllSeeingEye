import { useEffect, useRef, useState } from 'react';

import { useAccountRequest } from '@/components/account/useAccountRequest';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { fetchEvidencePackage } from '@/lib/api/reportDocuments';
import { describeError } from '@/lib/api/errors';
import { fileNameFor } from '@/lib/download';
import { saveBinaryFile } from '@/lib/downloadBinary';
import { subscribeWorkspaceAccess } from '@/lib/workspaceAccess';

export function EvidencePackageDownload({
  id,
  version,
  title,
}: {
  id: string;
  version: number;
  title: string;
}) {
  const request = useAccountRequest();
  const pending = useRef<AbortController | null>(null);
  useEffect(() => {
    const unsubscribe = subscribeWorkspaceAccess(() => pending.current?.abort());
    return () => {
      pending.current?.abort();
      unsubscribe();
    };
  }, []);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const download = async () => {
    if (busy) return;
    const controller = new AbortController();
    pending.current = controller;
    const signal = AbortSignal.any([request(), controller.signal]);
    setBusy(true);
    setError(null);
    try {
      const blob = await fetchEvidencePackage(id, version, signal);
      if (!signal.aborted)
        saveBinaryFile(fileNameFor(`${title}-v${String(version)}-evidence`, 'zip'), blob);
    } catch (caught) {
      if (!signal.aborted) setError(caught);
    } finally {
      if (!signal.aborted) setBusy(false);
    }
  };
  return (
    <div className="space-y-2">
      <Button variant="secondary" busy={busy} onClick={() => void download()}>
        Download evidence package
      </Button>
      <p className="text-xs text-muted">
        ZIP with this version, captured excerpts, source references, receipts and file hashes.
        Original source files are not included.
      </p>
      {error !== null && <Alert tone="error">{describeError(error)}</Alert>}
    </div>
  );
}

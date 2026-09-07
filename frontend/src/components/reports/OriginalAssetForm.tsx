import { useRef, useState } from 'react';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SelectField, TextAreaField, TextField } from '@/components/ui/Field';
import type { EvidenceItem } from '@/lib/api/reports';
import {
  deleteOriginalAsset,
  reserveOriginalAsset,
  uploadOriginalAsset,
} from '@/lib/api/originalAssets';
import { describeError } from '@/lib/api/errors';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';

const requestAborted = (signal: AbortSignal) => signal.aborted;

export function eligibleOriginals(evidence: EvidenceItem[]) {
  return evidence.filter((item) => {
    if (!['research_import', 'research_media'].includes(item.source_id)) return false;
    if (evidence.filter((other) => other.label === item.label).length !== 1) return false;
    const attributes = item.attributes ?? [];
    if (new Set(attributes.map((attribute) => attribute.key)).size !== attributes.length)
      return false;
    const hash = attributes.find((attribute) => attribute.key === 'original_sha256')?.value;
    const name = attributes.find((attribute) => attribute.key === 'filename')?.value;
    const media = attributes.find((attribute) => attribute.key === 'media_type')?.value;
    return (
      typeof hash === 'string' &&
      /^[a-f0-9]{64}$/i.test(hash) &&
      typeof name === 'string' &&
      name.length > 0 &&
      typeof media === 'string' &&
      media.length > 0
    );
  });
}

export function OriginalAssetForm({
  reportId,
  version,
  evidence,
  onSaved,
}: {
  reportId: string;
  version: number;
  evidence: EvidenceItem[];
  onSaved: () => void;
}) {
  const eligible = eligibleOriginals(evidence);
  const [label, setLabel] = useState(eligible[0]?.label ?? '');
  const [file, setFile] = useState<File | null>(null);
  const [use, setUse] = useState('');
  const [days, setDays] = useState('30');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [message, setMessage] = useState('');
  const [fileKey, setFileKey] = useState(0);
  const reservation = useRef<string | null>(null);
  const request = useScopedRequest();
  const clearFile = () => {
    setFile(null);
    setFileKey((value) => value + 1);
  };
  const cancel = async () => {
    const signal = request();
    const id = reservation.current;
    reservation.current = null;
    clearFile();
    setError(null);
    try {
      if (id) await deleteOriginalAsset(reportId, id, signal);
      if (!signal.aborted) {
        setMessage('Upload cancelled.');
        onSaved();
      }
    } catch (caught) {
      if (!signal.aborted) setError(caught);
    } finally {
      if (!signal.aborted) setBusy(false);
    }
  };
  const retain = async () => {
    if (busy || !file || !label || !use.trim()) return;
    const selected = eligible.find((item) => item.label === label);
    const filename = selected?.attributes?.find((attribute) => attribute.key === 'filename')?.value;
    const mediaType = selected?.attributes?.find(
      (attribute) => attribute.key === 'media_type',
    )?.value;
    if (typeof filename !== 'string' || typeof mediaType !== 'string') return;
    if (file.size < 1 || file.size > 8 * 1024 * 1024) {
      setError(new Error('Choose a non-empty original file no larger than 8 MiB.'));
      return;
    }
    const signal = request();
    setBusy(true);
    setError(null);
    setMessage('');
    let id: string | null = null;
    try {
      const reserved = await reserveOriginalAsset(
        reportId,
        {
          version_number: version,
          evidence_label: label,
          filename,
          media_type: mediaType,
          byte_count: file.size,
          permitted_use: use.trim(),
          retention_days: Number(days),
        },
        signal,
      );
      signal.throwIfAborted();
      id = reserved.id;
      reservation.current = id;
      const retained = await uploadOriginalAsset(reportId, id, file, signal);
      signal.throwIfAborted();
      if (retained.status !== 'active')
        throw new Error('The original was not retained. Refresh the list to check its status.');
      reservation.current = null;
      clearFile();
      setUse('');
      setMessage(
        `Original bytes matched the frozen SHA-256 for ${retained.evidence_label}. File retained.`,
      );
      onSaved();
    } catch (caught) {
      if (!signal.aborted) {
        setError(caught);
        if (id) {
          try {
            await deleteOriginalAsset(reportId, id, signal);
          } catch {
            /* Abandoned reservations expire on the server after two minutes. */
          }
        }
        if (!requestAborted(signal)) {
          reservation.current = null;
          clearFile();
          onSaved();
        }
      }
    } finally {
      if (!signal.aborted) setBusy(false);
    }
  };
  if (!eligible.length)
    return (
      <p className="text-sm text-muted">
        This version has no eligible imported original-file hash. Import a document or media file
        into research first.
      </p>
    );
  return (
    <form
      className="space-y-3 rounded border border-line p-4"
      onSubmit={(event) => {
        event.preventDefault();
        void retain();
      }}
    >
      <h4 className="font-medium">Retain a selected original</h4>
      <SelectField
        label="Imported evidence"
        value={label}
        disabled={busy}
        onChange={(event) => setLabel(event.target.value)}
        options={eligible.map((item) => ({
          value: item.label,
          label: `${item.label} · ${item.title}`,
        }))}
      />
      <TextField
        key={fileKey}
        label="Original file"
        type="file"
        disabled={busy}
        onChange={(event) => setFile(event.target.files?.[0] ?? null)}
        hint="Up to 8 MiB. The server must match these exact bytes to the original hash frozen in this report version."
      />
      <TextAreaField
        label="Permitted-use declaration"
        value={use}
        maxLength={1000}
        required
        disabled={busy}
        onChange={(event) => setUse(event.target.value)}
        hint="Record why you are permitted to retain and share this file. This is your declaration, not verified legal permission."
      />
      <TextField
        label="Retention days"
        type="number"
        min={1}
        max={90}
        required
        value={days}
        disabled={busy}
        onChange={(event) => setDays(event.target.value)}
      />
      <p className="text-xs text-muted">
        Retention is 1–90 days. Deletion and expiry remove stored bytes; independent backups may
        retain historical copies. Interrupted reservations expire after two minutes.
      </p>
      <div className="flex gap-2">
        <Button type="submit" busy={busy} disabled={!file || !use.trim()}>
          Retain original
        </Button>
        {busy && (
          <Button type="button" variant="secondary" onClick={() => void cancel()}>
            Cancel upload
          </Button>
        )}
      </div>
      {error !== null && (
        <Alert tone="error">{error instanceof Error ? error.message : describeError(error)}</Alert>
      )}
      {message && (
        <p role="status" className="text-sm">
          {message}
        </p>
      )}
    </form>
  );
}

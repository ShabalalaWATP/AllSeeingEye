import { Button } from '@/components/ui/Button';
import { formatUtc } from '@/lib/format';
import type { ResearchInputReceipt } from '@/lib/api/researchInputs';
export function SecAttachmentSummary({
  receipt,
  originalExpiresAt,
  disabled,
  downloading,
  onDownload,
  onRemove,
}: {
  receipt: ResearchInputReceipt;
  originalExpiresAt: string;
  disabled: boolean;
  downloading: boolean;
  onDownload: () => void;
  onRemove: () => void;
}) {
  return (
    <section
      aria-label="Imported SEC filing document"
      className="space-y-3 rounded border border-line p-4"
    >
      <h3 className="font-medium">Attached filing document: {receipt.filename}</h3>
      <p className="text-sm">
        {receipt.event_count} extracted passages; {receipt.extracted_characters.toLocaleString()}{' '}
        characters. Research uses this imported document, not just the filing listing.
      </p>
      <p className="text-xs text-muted">
        Extracted input expires {formatUtc(receipt.expires_at)}. Selected text is sent to your
        configured analysis model when research starts and retained as report evidence.
      </p>
      <p className="text-xs text-muted">
        The original document is available only temporarily, until {formatUtc(originalExpiresAt)}. A
        download is a local copy; this does not preserve the original permanently in the app.
      </p>
      <div className="flex flex-wrap gap-2">
        <Button variant="secondary" disabled={disabled} busy={downloading} onClick={onDownload}>
          Download temporary original document
        </Button>
        <Button variant="ghost" disabled={disabled || downloading} onClick={onRemove}>
          Remove filing attachment
        </Button>
      </div>
      <details>
        <summary className="cursor-pointer text-sm">
          Extracted document preview and limitations
        </summary>
        <p className="whitespace-pre-wrap break-words text-xs">
          {receipt.preview || 'No text preview available.'}
        </p>
        <ul className="list-disc space-y-1 pl-4 text-xs">
          {receipt.limitations.map((limit, index) => (
            <li key={index}>{limit}</li>
          ))}
        </ul>
        <p className="break-all font-mono text-xs">Document SHA-256: {receipt.sha256}</p>
      </details>
    </section>
  );
}

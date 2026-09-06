import { useEffect, useId, useRef } from 'react';

import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { formatUtc } from '@/lib/format';

import { IMPORT_EXTENSIONS, useResearchInput } from './useResearchInput';

export interface ResearchInputProps {
  onChange: (inputId: string | null) => void;
  onBusyChange?: (busy: boolean) => void;
  disabled?: boolean;
}

/** One private attachment, with explicit expiry and only server-sanitised media previews. */
export function ResearchInput({ onChange, onBusyChange, disabled = false }: ResearchInputProps) {
  const input = useResearchInput(onChange);
  const id = useId();
  const busyChanged = useRef(onBusyChange);
  useEffect(() => {
    busyChanged.current = onBusyChange;
  }, [onBusyChange]);
  useEffect(() => {
    busyChanged.current?.(input.busy);
    return () => busyChanged.current?.(false);
  }, [input.busy]);
  const receipt = input.receipt;
  return (
    <section
      aria-label="Research attachment"
      className="min-w-0 space-y-3 border-t border-line pt-5"
    >
      <div>
        <label htmlFor={id} className="text-sm font-medium">
          Document or media
        </label>
        <p id={`${id}-help`} className="mt-1 text-xs leading-relaxed text-muted">
          One file up to 8 MiB. TXT, CSV, JSON, PDF, DOCX, PNG, JPEG, WebP, MP4, MOV or WebM.
        </p>
      </div>
      <input
        key={input.key}
        id={id}
        type="file"
        accept={IMPORT_EXTENSIONS}
        disabled={disabled}
        aria-describedby={`${id}-help ${id}-retention`}
        className="block w-full min-w-0 text-xs text-muted file:mr-3 file:rounded-md file:border file:border-line file:bg-surface-2 file:px-3 file:py-2 file:text-sm file:font-medium file:text-text focus-visible:outline-2 focus-visible:outline-ember disabled:opacity-50"
        onChange={(event) => {
          const file = event.currentTarget.files?.[0];
          event.currentTarget.value = '';
          if (file !== undefined) void input.upload(file);
        }}
      />
      <p id={`${id}-retention`} className="text-xs leading-relaxed text-muted">
        The original file is discarded after processing. Extracted text and previews expire after 15
        minutes. Selected text is sent to your configured analysis model when you run research and
        preserved as evidence with the report.
      </p>
      {input.busy && (
        <div className="flex flex-wrap items-center gap-3">
          <p role="status" className="min-w-0 break-all text-sm">
            Uploading and extracting {input.filename}…
          </p>
          <Button variant="secondary" onClick={() => input.clear('cancelled')}>
            Cancel import
          </Button>
        </div>
      )}
      {input.error !== null && <Alert tone="error">{input.error}</Alert>}
      {input.status === 'cancelled' && (
        <p role="status" className="text-sm text-muted">
          Import cancelled.
        </p>
      )}
      {input.status === 'expired' && (
        <Alert tone="warning">
          This attachment has expired. Choose the file again to include it.
        </Alert>
      )}
      {receipt !== null && (
        <div className="space-y-3">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <p role="status" className="break-all text-sm font-medium">
                Attached: {receipt.filename}
              </p>
              <p className="mt-1 text-xs text-muted">
                {receipt.event_count} extracted passages ·{' '}
                {receipt.extracted_characters.toLocaleString()} characters
              </p>
              <p className="mt-1 text-xs text-muted">Expires {formatUtc(receipt.expires_at)}</p>
            </div>
            <Button variant="ghost" disabled={disabled} onClick={() => input.clear()}>
              Remove attachment
            </Button>
          </div>
          {(receipt.previews ?? []).length > 0 && (
            <div className="grid max-w-xl grid-cols-1 gap-3 sm:grid-cols-3">
              {(receipt.previews ?? []).map((frame, index) => (
                <figure key={`${frame.sha256}:${index}`} className="min-w-0">
                  <img
                    src={`data:image/png;base64,${frame.png_base64}`}
                    alt={`Sanitised preview ${index + 1} of ${receipt.filename}`}
                    className="max-h-48 w-full rounded object-contain"
                  />
                  <figcaption className="mt-1 text-xs text-muted">
                    {receipt.media_type.startsWith('video/')
                      ? `Frame at ${frame.seconds.toFixed(1)} seconds`
                      : 'Resized, metadata-stripped preview'}
                  </figcaption>
                </figure>
              ))}
            </div>
          )}
          <details className="text-xs text-muted">
            <summary className="cursor-pointer py-2 font-medium text-text">
              Extraction preview and limitations
            </summary>
            <p className="mt-2 whitespace-pre-wrap break-words">
              {receipt.preview || 'No text preview available.'}
            </p>
            <ul className="mt-3 list-disc space-y-1 pl-4">
              {receipt.limitations.map((limit, index) => (
                <li key={index}>{limit}</li>
              ))}
            </ul>
            <p className="mt-3 break-all font-mono text-[11px]">SHA-256: {receipt.sha256}</p>
          </details>
        </div>
      )}
    </section>
  );
}

import { useId } from 'react';

import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { formatUtc } from '@/lib/format';

import { MAX_PHOTOS, PHOTO_EXTENSIONS, type usePhotoInputs } from './usePhotoInputs';

export function PhotoGeolocationUpload({
  input,
  disabled,
  onUpload,
  onRemove,
  validation,
}: {
  input: ReturnType<typeof usePhotoInputs>;
  disabled: boolean;
  onUpload: (files: readonly File[]) => void;
  onRemove: (id: string) => void;
  validation: string | null;
}) {
  const id = useId();
  return (
    <section aria-label="Photo attachments" className="min-w-0 space-y-4">
      <div className="flex items-baseline justify-between gap-3">
        <label htmlFor={id} className="text-sm font-semibold">
          {input.receipts.length === 1 ? 'Photograph' : 'Photographs'}
        </label>
        <span className="font-mono text-xs text-muted">
          {input.receipts.length} / {MAX_PHOTOS} photos
        </span>
      </div>
      <p id={`${id}-limits`} className="text-xs leading-relaxed text-muted">
        Select up to six PNG, JPEG or WebP photos together. Each photo: up to 8 MiB, 8 megapixels
        and 8,192 pixels on either edge. Static images only. Choosing files replaces this set.
      </p>
      <input
        key={input.key}
        id={id}
        type="file"
        multiple
        accept={PHOTO_EXTENSIONS}
        disabled={disabled || input.busy}
        aria-describedby={`${id}-limits ${id}-privacy`}
        className="block w-full min-w-0 text-xs text-muted file:mr-3 file:rounded-md file:border file:border-line file:bg-surface-2 file:px-3 file:py-2 file:text-sm file:font-medium file:text-text focus-visible:outline-2 focus-visible:outline-ember disabled:opacity-50"
        onChange={(event) => {
          const files = Array.from(event.currentTarget.files ?? []);
          event.currentTarget.value = '';
          if (files.length) onUpload(files);
        }}
      />
      {input.receipts.length ? (
        <ol className="grid grid-cols-2 gap-3" aria-label="Selected photographs">
          {input.receipts.map((receipt, index) => (
            <li
              key={receipt.id}
              className={input.receipts.length === 1 ? 'col-span-2 min-w-0' : 'min-w-0'}
            >
              <div className="relative flex aspect-[4/3] items-center justify-center overflow-hidden rounded-lg bg-ground">
                {receipt.previews?.[0] ? (
                  <img
                    src={`data:image/png;base64,${receipt.previews[0].png_base64}`}
                    alt={`Sanitised preview of ${receipt.filename}`}
                    className="h-full w-full object-contain"
                  />
                ) : (
                  <p className="p-4 text-center text-xs text-muted">No usable preview extracted</p>
                )}
                <span className="absolute left-2 top-2 rounded bg-ground/90 px-2 py-1 font-mono text-xs text-text">
                  Photo {index + 1}
                </span>
              </div>
              <div className="mt-2 flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p role="status" className="break-all text-xs font-medium">
                    Photo ready: {receipt.filename}
                  </p>
                  <p className="mt-1 text-[11px] text-muted">
                    Expires {formatUtc(receipt.expires_at)}
                  </p>
                </div>
                <Button
                  variant="ghost"
                  disabled={disabled || input.busy}
                  onClick={() => onRemove(receipt.id)}
                  aria-label={
                    input.receipts.length === 1 ? 'Remove photo' : `Remove photo ${index + 1}`
                  }
                >
                  Remove
                </Button>
              </div>
            </li>
          ))}
        </ol>
      ) : (
        <div className="flex min-h-60 items-center justify-center rounded-lg border border-dashed border-line bg-ground/40">
          <div className="max-w-64 p-6 text-center">
            <p className="text-sm font-medium">Add your visual evidence</p>
            <p className="mt-2 text-xs leading-relaxed text-muted">
              Compare landscapes, signs and landmarks across several views of a location.
            </p>
          </div>
        </div>
      )}
      {input.busy && (
        <div className="flex flex-wrap items-center gap-3">
          <p role="status" className="min-w-0 break-all text-sm">
            {input.filename ? `Preparing ${input.filename}…` : 'Updating photo selection…'}
          </p>
          <Button variant="secondary" onClick={() => input.clear('cancelled')}>
            Cancel upload
          </Button>
        </div>
      )}
      <p id={`${id}-privacy`} className="text-xs leading-relaxed text-muted">
        Originals are discarded after extraction. Text and sanitised previews expire after 15
        minutes. Photos are sent to your configured model only when you consent and start analysis.
      </p>
      {validation && <Alert tone="error">{validation}</Alert>}
      {input.error && <Alert tone="error">{input.error}</Alert>}
      {input.status === 'cancelled' && (
        <p role="status" className="text-sm text-muted">
          Photo upload cancelled.
        </p>
      )}
      {input.status === 'expired' && (
        <Alert tone="warning">
          This photo has expired. Choose the files again to analyse or save the set.
        </Alert>
      )}
    </section>
  );
}

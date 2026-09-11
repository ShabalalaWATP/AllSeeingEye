import { useId } from 'react';

import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { formatUtc } from '@/lib/format';

import type { useResearchInput } from './useResearchInput';

export const PHOTO_EXTENSIONS = '.png,.jpg,.jpeg,.webp';

export function PhotoGeolocationUpload({
  input,
  disabled,
  onUpload,
  onRemove,
  validation,
}: {
  input: ReturnType<typeof useResearchInput>;
  disabled: boolean;
  onUpload: (file: File) => void;
  onRemove: () => void;
  validation: string | null;
}) {
  const id = useId();
  const receipt = input.receipt;
  const preview = receipt?.previews?.[0];
  return (
    <section aria-label="Photo attachment" className="min-w-0 space-y-4">
      <div className="flex items-baseline justify-between gap-3">
        <label htmlFor={id} className="text-sm font-semibold">
          Photograph
        </label>
        <span className="text-xs text-muted">PNG, JPEG or WebP · up to 8 MiB</span>
      </div>
      <input
        key={input.key}
        id={id}
        type="file"
        accept={PHOTO_EXTENSIONS}
        disabled={disabled}
        aria-describedby={`${id}-privacy`}
        className="block w-full min-w-0 text-xs text-muted file:mr-3 file:rounded-md file:border file:border-line file:bg-surface-2 file:px-3 file:py-2 file:text-sm file:font-medium file:text-text focus-visible:outline-2 focus-visible:outline-ember disabled:opacity-50"
        onChange={(event) => {
          const file = event.currentTarget.files?.[0];
          event.currentTarget.value = '';
          if (file) onUpload(file);
        }}
      />
      <div className="flex min-h-52 items-center justify-center overflow-hidden rounded-lg bg-ground">
        {preview ? (
          <img
            src={`data:image/png;base64,${preview.png_base64}`}
            alt={`Sanitised preview of ${receipt.filename}`}
            className="max-h-80 w-full object-contain"
          />
        ) : (
          <p className="max-w-56 p-6 text-center text-sm leading-relaxed text-muted">
            {input.busy
              ? 'Preparing a safe photo preview…'
              : 'Choose a photo to inspect its landscape, signs and landmarks.'}
          </p>
        )}
      </div>
      {input.busy && (
        <div className="flex flex-wrap items-center gap-3">
          <p role="status" className="min-w-0 break-all text-sm">
            Preparing {input.filename}…
          </p>
          <Button variant="secondary" onClick={() => input.clear('cancelled')}>
            Cancel upload
          </Button>
        </div>
      )}
      {receipt && (
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <p role="status" className="break-all text-sm font-medium">
              Photo ready: {receipt.filename}
            </p>
            <p className="mt-1 text-xs text-muted">Expires {formatUtc(receipt.expires_at)}</p>
          </div>
          <Button variant="ghost" disabled={disabled} onClick={onRemove}>
            Remove photo
          </Button>
        </div>
      )}
      <p id={`${id}-privacy`} className="text-xs leading-relaxed text-muted">
        The app discards the original after extraction. Text and sanitised previews expire after 15
        minutes. The photo is sent to your configured model only when you consent and start
        analysis.
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
          This photo has expired. Choose the file again to analyse or save it.
        </Alert>
      )}
    </section>
  );
}

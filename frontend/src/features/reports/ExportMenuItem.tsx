import { useId } from 'react';

import type { ExportChoice, ExportDescription } from './exportFormats';

/** One export format: what it is for, and any limitation that applies to it. */
export function ExportMenuItem({
  format,
  description,
  preferred,
  busy,
  caveat,
  unavailableReason = null,
  onSelect,
}: {
  format: ExportChoice;
  description: ExportDescription;
  preferred: boolean;
  busy: boolean;
  caveat: string | null;
  /** Why the item cannot be chosen yet; shown and announced while it is disabled. */
  unavailableReason?: string | null;
  onSelect: () => void;
}) {
  const caveatId = caveat ? `export-caveat-${format}` : undefined;
  const reasonId = useId();
  const describedBy = [unavailableReason ? reasonId : null, caveatId ?? null]
    .filter((id) => id !== null)
    .join(' ');
  return (
    <button
      type="button"
      role="menuitem"
      aria-label={`Download ${description.short}`}
      {...(describedBy ? { 'aria-describedby': describedBy } : {})}
      disabled={busy || unavailableReason !== null}
      className="flex w-full flex-col gap-1 rounded px-2 py-3 text-left transition-colors hover:bg-surface-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-ember disabled:opacity-50 motion-reduce:transition-none"
      onClick={onSelect}
    >
      <span className="flex w-full items-center justify-between gap-3">
        <span className="text-sm font-medium text-text">{description.label}</span>
        <span className="flex shrink-0 items-center gap-1.5">
          {caveat && (
            <span className="rounded-full bg-amber/15 px-2 py-0.5 text-2xs font-medium uppercase tracking-wide text-amber">
              Limited
            </span>
          )}
          {preferred && (
            <span className="rounded-full bg-ember/15 px-2 py-0.5 text-2xs font-medium uppercase tracking-wide text-ember">
              Preferred
            </span>
          )}
          <span className="text-2xs uppercase tracking-wide text-muted">{description.purpose}</span>
        </span>
      </span>
      <span className="block text-xs leading-5 text-muted">{description.detail}</span>
      {unavailableReason && (
        <span id={reasonId} className="block text-xs leading-5 text-text">
          {unavailableReason}
        </span>
      )}
      {caveat && (
        <span id={caveatId} className="block text-xs leading-5 text-amber">
          {caveat}
        </span>
      )}
    </button>
  );
}

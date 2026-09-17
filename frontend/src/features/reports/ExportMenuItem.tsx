import type { ExportChoice, ExportDescription } from './exportFormats';

/** One export format: what it is for, and any limitation that applies to it. */
export function ExportMenuItem({
  format,
  description,
  preferred,
  busy,
  caveat,
  onSelect,
}: {
  format: ExportChoice;
  description: ExportDescription;
  preferred: boolean;
  busy: boolean;
  caveat: string | null;
  onSelect: () => void;
}) {
  const caveatId = caveat ? `export-caveat-${format}` : undefined;
  return (
    <button
      type="button"
      role="menuitem"
      aria-label={`Download ${description.short}`}
      {...(caveatId ? { 'aria-describedby': caveatId } : {})}
      disabled={busy}
      className="flex w-full flex-col gap-1 rounded px-2 py-3 text-left transition-colors hover:bg-surface-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-ember disabled:opacity-50 motion-reduce:transition-none"
      onClick={onSelect}
    >
      <span className="flex w-full items-center justify-between gap-3">
        <span className="text-sm font-medium text-text">{description.label}</span>
        <span className="flex shrink-0 items-center gap-1.5">
          {caveat && (
            <span className="rounded-full bg-amber/15 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-amber">
              Limited
            </span>
          )}
          {preferred && (
            <span className="rounded-full bg-ember/15 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-ember">
              Preferred
            </span>
          )}
          <span className="text-[11px] uppercase tracking-wide text-muted">
            {description.purpose}
          </span>
        </span>
      </span>
      <span className="block text-xs leading-5 text-muted">{description.detail}</span>
      {caveat && (
        <span id={caveatId} className="block text-xs leading-5 text-amber">
          {caveat}
        </span>
      )}
    </button>
  );
}

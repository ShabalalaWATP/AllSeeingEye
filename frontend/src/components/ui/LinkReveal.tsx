import { formatUtc } from '@/lib/format';

import { Button } from './Button';
import { CopyButton } from './CopyButton';

export interface LinkRevealProps {
  title: string;
  link: string;
  expiresAt: string;
  /** Shows a dismiss control, for pages that keep several revealed links. */
  onDismiss?: (() => void) | undefined;
}

/**
 * Shows a one-time link (activation or reset) with a copy button and its expiry.
 * The link is rendered as text in a read-only input so it can be selected by hand.
 */
export function LinkReveal({ title, link, expiresAt, onDismiss }: LinkRevealProps) {
  return (
    <div
      role="status"
      className="flex flex-col gap-2 rounded-md border border-good/40 bg-good/10 px-3 py-2 text-sm"
    >
      <div className="flex items-start justify-between gap-2">
        <p className="font-semibold">{title}</p>
        {onDismiss === undefined ? null : (
          <Button variant="ghost" aria-label={`Dismiss ${title}`} onClick={onDismiss}>
            Dismiss
          </Button>
        )}
      </div>
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
        <input
          readOnly
          aria-label={title}
          value={link}
          className="w-full rounded-md border border-control-border bg-ground px-2 py-1 font-mono text-xs text-text"
          onFocus={(event) => {
            event.currentTarget.select();
          }}
        />
        <CopyButton value={link} />
      </div>
      <p className="text-xs text-muted">Expires {formatUtc(expiresAt)}</p>
    </div>
  );
}

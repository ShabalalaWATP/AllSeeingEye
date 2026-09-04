import { formatUtc } from '@/lib/format';

import { CopyButton } from './CopyButton';

export interface LinkRevealProps {
  title: string;
  link: string;
  expiresAt: string;
}

/**
 * Shows a one-time link (activation or reset) with a copy button and its expiry.
 * The link is rendered as text in a read-only input so it can be selected by hand.
 */
export function LinkReveal({ title, link, expiresAt }: LinkRevealProps) {
  return (
    <div
      role="status"
      className="flex flex-col gap-2 rounded-md border border-good/40 bg-good/10 px-3 py-2 text-sm"
    >
      <p className="font-semibold">{title}</p>
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
        <input
          readOnly
          aria-label={title}
          value={link}
          className="w-full rounded-md border border-line bg-ground px-2 py-1 font-mono text-xs text-text"
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

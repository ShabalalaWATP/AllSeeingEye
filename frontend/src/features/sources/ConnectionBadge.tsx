import type { ConnectionState } from '@/lib/api/sourceContext';
import { CONNECTION_META, TONE_CLASSES } from './connectionPresentation';

/** A small labelled pill; the dot repeats the tone so colour is never the only signal. */
export function ConnectionBadge({
  state,
  optional = false,
}: {
  state: ConnectionState;
  optional?: boolean;
}) {
  const meta = CONNECTION_META[state];
  const label =
    optional && (state === 'key_missing' || state === 'not_configured')
      ? 'Optional, not set'
      : meta.label;
  const tone = optional && meta.group === 'key_missing' ? 'muted' : meta.tone;
  return (
    <span
      className={`inline-flex shrink-0 items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-medium whitespace-nowrap ${TONE_CLASSES[tone]}`}
    >
      <span aria-hidden="true" className="size-1.5 rounded-full bg-current" />
      {label}
    </span>
  );
}

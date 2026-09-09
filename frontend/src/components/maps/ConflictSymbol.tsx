import type { ConflictKind } from '@/lib/conflicts';
import { CONFLICT_SYMBOLS } from '@/lib/conflictSymbols';

/** Shared map symbol and filter legend. The adjacent text provides its accessible name. */
export function ConflictSymbol({
  kind,
  className = 'h-5 w-5 shrink-0',
}: {
  kind: ConflictKind;
  className?: string;
}) {
  const symbol = CONFLICT_SYMBOLS[kind];
  return (
    <svg
      aria-hidden="true"
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke={symbol.css}
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d={symbol.path} />
    </svg>
  );
}

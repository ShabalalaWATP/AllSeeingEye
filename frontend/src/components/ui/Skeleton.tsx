/**
 * Placeholder lines shaped like the content that is loading, so the layout does not jump
 * when it arrives. Purely visual: it is hidden from assistive technology, so always pair it
 * with a status message such as `LoadingNote`. The pulse stops under reduced motion through
 * the global rule in theme.css.
 */
const WIDTHS = ['w-full', 'w-11/12', 'w-4/5', 'w-2/3'] as const;

export interface SkeletonProps {
  /** How many lines to draw. */
  lines?: number | undefined;
  className?: string | undefined;
}

export function Skeleton({ lines = 3, className = '' }: SkeletonProps) {
  return (
    <div aria-hidden="true" data-skeleton="" className={`flex flex-col gap-2 ${className}`}>
      {Array.from({ length: lines }, (_, index) => (
        <div
          key={index}
          className={`h-3 animate-pulse rounded bg-surface-2 ${WIDTHS[index % WIDTHS.length]}`}
        />
      ))}
    </div>
  );
}

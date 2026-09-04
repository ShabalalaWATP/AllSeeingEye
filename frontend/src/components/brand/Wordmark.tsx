export interface WordmarkProps {
  className?: string;
}

/** "THE ALL SEEING EYE" in JetBrains Mono, set beside the mark. */
export function Wordmark({ className = '' }: WordmarkProps) {
  return (
    <span
      className={`font-mono text-xs font-semibold uppercase tracking-[0.28em] text-text ${className}`}
    >
      The All Seeing Eye
    </span>
  );
}

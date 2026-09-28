export type Basis = 'claimed' | 'assessed' | 'visually_confirmed' | 'documented' | 'reported';

/**
 * Accent tokens (amber, cyan, muted) are text colours in every theme. Chart colours are data
 * colours that fall below AA on some surfaces, so they mark the border and a dot instead of
 * the words.
 */
const LABELS: Record<Basis, { label: string; className: string; dot?: string; title: string }> = {
  claimed: {
    label: 'Claimed',
    className: 'border-amber/60 text-amber',
    title: "A party to the conflict's own figure, not independently verified.",
  },
  assessed: {
    label: 'Assessed',
    className: 'border-cyan/60 text-cyan',
    title: "A named research body's judgement, not an observed fact.",
  },
  visually_confirmed: {
    label: 'Visually confirmed',
    className: 'border-chart-3/60 text-text',
    dot: 'bg-chart-3',
    title: 'Counted from published photographs or video; an undercount by design.',
  },
  documented: {
    label: 'Documented',
    className: 'border-chart-5/60 text-text',
    dot: 'bg-chart-5',
    title: 'Recorded by a UN body or court from named cases.',
  },
  reported: {
    label: 'Reported',
    className: 'border-line text-muted',
    title: 'Press or public map reporting, not verification.',
  },
};

/** States who stands behind a figure or line, so no number reads as verified by default. */
export function BasisBadge({ basis }: { basis: Basis }) {
  const { label, className, dot, title } = LABELS[basis];
  return (
    <span
      title={title}
      className={`inline-flex items-center gap-1.5 rounded border px-1.5 py-0.5 font-mono text-2xs uppercase tracking-wide ${className}`}
    >
      {dot ? <span aria-hidden="true" className={`size-1.5 shrink-0 rounded-full ${dot}`} /> : null}
      {label}
    </span>
  );
}

export type Basis = 'claimed' | 'assessed' | 'visually_confirmed' | 'documented' | 'reported';

const LABELS: Record<Basis, { label: string; className: string; title: string }> = {
  claimed: {
    label: 'Claimed',
    className: 'border-amber-300/60 text-amber-300',
    title: "A party to the conflict's own figure, not independently verified.",
  },
  assessed: {
    label: 'Assessed',
    className: 'border-cyan/60 text-cyan',
    title: "A named research body's judgement, not an observed fact.",
  },
  visually_confirmed: {
    label: 'Visually confirmed',
    className: 'border-chart-3/60 text-chart-3',
    title: 'Counted from published photographs or video; an undercount by design.',
  },
  documented: {
    label: 'Documented',
    className: 'border-chart-5/60 text-chart-5',
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
  const { label, className, title } = LABELS[basis];
  return (
    <span
      title={title}
      className={`inline-flex items-center rounded border px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wide ${className}`}
    >
      {label}
    </span>
  );
}

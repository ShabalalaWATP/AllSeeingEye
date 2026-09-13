import { portraitUrl, type PlacementBasis, type PublicFigure } from '@/lib/api/figures';

const RING: Record<PlacementBasis, string> = {
  reported_place: 'ring-cyan',
  reported_country: 'ring-amber-300',
  seat: 'ring-muted/60',
};

/** A circular portrait whose ring colour states the placement basis, or an initial when absent. */
export function FigurePortrait({
  figure,
  size = 'md',
}: {
  figure: Pick<PublicFigure, 'name' | 'portrait' | 'placement'>;
  size?: 'sm' | 'md' | 'lg';
}) {
  const url = portraitUrl(figure);
  const dimension = size === 'lg' ? 'size-16' : size === 'md' ? 'size-10' : 'size-7';
  const ring = RING[figure.placement.basis];
  return url ? (
    <img
      src={url}
      alt=""
      width={64}
      height={64}
      className={`${dimension} shrink-0 rounded-full bg-surface-2 ring-2 ${ring}`}
    />
  ) : (
    <span
      aria-hidden="true"
      className={`${dimension} flex shrink-0 items-center justify-center rounded-full bg-surface-2 font-mono text-xs text-muted ring-2 ${ring}`}
    >
      {figure.name.slice(0, 1)}
    </span>
  );
}

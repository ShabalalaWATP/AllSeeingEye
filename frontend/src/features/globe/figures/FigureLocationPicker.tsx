import { useId } from 'react';
import { BASIS_LABELS, type PublicFigure } from '@/lib/api/figures';

/** Match shared placements exactly; nearby reports must not become invented shared locations. */
export function figuresAtLocation(figures: readonly PublicFigure[], selected: PublicFigure) {
  return figures.filter(
    ({ placement }) =>
      placement.latitude === selected.placement.latitude &&
      placement.longitude === selected.placement.longitude,
  );
}

export function FigureLocationPicker({
  figure,
  visibleFigures,
  onSelect,
}: {
  figure: PublicFigure;
  visibleFigures: readonly PublicFigure[];
  onSelect: (figure: PublicFigure) => void;
}) {
  const id = useId();
  const figures = figuresAtLocation(visibleFigures, figure);
  if (figures.length < 2) return null;
  return (
    <div className="mt-3 rounded border border-line p-2 text-xs">
      <label htmlFor={id} className="block font-medium">
        Figure at this map location
      </label>
      <select
        id={id}
        value={figure.id}
        aria-describedby={`${id}-note`}
        className="mt-2 min-h-11 w-full rounded border border-line bg-surface p-2 text-text focus-visible:outline-2 focus-visible:outline-cyan"
        onChange={(event) => {
          const next = figures.find((item) => item.id === event.target.value);
          if (next) onSelect(next);
        }}
      >
        {figures.map((item) => (
          <option key={item.id} value={item.id}>
            {item.name} · {item.office} · {BASIS_LABELS[item.placement.basis]}
          </option>
        ))}
      </select>
      <p id={`${id}-note`} className="mt-2 text-muted">
        {figures.length} visible figures share this map placement. This does not mean they are
        together.
      </p>
    </div>
  );
}

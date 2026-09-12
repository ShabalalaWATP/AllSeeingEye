import { Link } from 'react-router';
import type { useSavedMapArea } from './useSavedMapArea';

export function SavedMapAreaNotice({ area }: { area: ReturnType<typeof useSavedMapArea> }) {
  if (!area.id) return null;
  return (
    <aside
      aria-label="Saved map area"
      className="absolute top-16 left-1/2 z-20 flex max-w-[65%] -translate-x-1/2 items-center gap-3 rounded-lg border border-line bg-surface px-4 py-2 text-xs shadow-lg"
    >
      <div>
        {area.area && <strong className="block">{area.area.name}</strong>}
        <p className="text-muted">{area.message}</p>
        <Link className="text-ember hover:underline" to="/direction">
          Plans & areas
        </Link>
      </div>
      <button
        type="button"
        aria-label="Close saved area"
        className="min-h-10 px-2"
        onClick={area.close}
      >
        Close
      </button>
    </aside>
  );
}

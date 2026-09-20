import type { MeasurementControls } from '@/components/maps/MapMeasurementPanel';
/** Keep measurement actions reachable while the tool inspector is collapsed. */
export function MeasurementReadout({ value }: { value: MeasurementControls }) {
  return (
    value.picking && (
      <section
        aria-label="Active measurement"
        className="absolute bottom-28 left-1/2 z-10 w-max max-w-[calc(100%-7.5rem)] -translate-x-1/2 rounded border border-cyan bg-ground px-3 py-2 text-xs text-cyan"
      >
        <p aria-live="polite" className="break-words font-mono text-lg">
          {value.result}
        </p>
        <div className="flex flex-wrap items-center gap-3">
          <span>{value.points.length}/32 points</span>
          <button
            type="button"
            onClick={value.undo}
            disabled={!value.points.length}
            className="min-h-9 underline disabled:opacity-40"
          >
            Undo point
          </button>
          <button
            type="button"
            onClick={() => value.setPicking(false)}
            className="min-h-9 font-medium underline"
          >
            Finish measuring
          </button>
        </div>
      </section>
    )
  );
}

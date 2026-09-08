import type { MeasurementControls } from '@/components/maps/MapMeasurementPanel';
/** Keep the live result reachable while the settings panel is closed. */
export function MeasurementReadout({ value }: { value: MeasurementControls }) {
  return (
    value.picking && (
      <button
        type="button"
        onClick={() => value.setPicking(false)}
        className="absolute bottom-28 left-1/2 z-10 w-max max-w-[calc(100%-7.5rem)] -translate-x-1/2 rounded border border-cyan bg-ground px-3 py-2 text-xs text-cyan"
      >
        {value.result} · {value.points.length}/32 points · Stop measuring
      </button>
    )
  );
}

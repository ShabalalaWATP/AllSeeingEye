import type { LiveEvent } from '@/lib/api/eventSchemas';
import { isHistoricalConflict } from '@/lib/conflicts';

export function HistoricalBaselineNote({ event }: { event: LiveEvent }) {
  if (!isHistoricalConflict(event)) return null;
  const text = (name: string) => {
    const value = event.attributes[name];
    return typeof value === 'string' || typeof value === 'number' ? String(value) : 'Unknown';
  };
  return (
    <p className="my-2 rounded-md border border-amber-400/25 bg-amber-400/5 p-2 text-xs text-amber-200">
      Historical baseline, not a live incident. Provisional monthly dataset{' '}
      {text('dataset_version')}; coverage {text('coverage_start')} to {text('coverage_end')}.
      Occurred: {text('occurrence_start')}.
    </p>
  );
}

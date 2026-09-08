import type { LiveEvent } from '@/lib/api/eventSchemas';
import type { JamCell } from '@/lib/api/aviation';
import { EventInspector } from './EventInspector';
import { MapDetailsInspector } from './MapDetailsInspector';
import type { MapDetails } from './MapDetailsInspector';

/** A single inspection surface for a selected event, overlap or accuracy cell. */
export function SelectedMapDetails({
  selected,
  storySize,
  details,
  events,
  cells,
  updatedAt,
  interference,
  onSelect,
  onClose,
}: {
  selected: LiveEvent | null;
  storySize: number;
  details: MapDetails | null;
  events: readonly LiveEvent[];
  cells: readonly JamCell[];
  updatedAt: string | null;
  interference: boolean;
  onSelect: (event: LiveEvent) => void;
  onClose: () => void;
}) {
  if (selected) return <EventInspector event={selected} storySize={storySize} onClose={onClose} />;
  if (!details || (details.kind === 'jam' && !interference)) return null;
  return (
    <MapDetailsInspector
      key={
        details.kind === 'cluster' ? details.cluster.id : `${details.cell.lon}:${details.cell.lat}`
      }
      details={details}
      events={events}
      cells={cells}
      updatedAt={updatedAt}
      onSelect={onSelect}
      onClose={onClose}
    />
  );
}

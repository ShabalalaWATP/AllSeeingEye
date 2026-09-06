import { Button } from '@/components/ui/Button';
import { Alert } from '@/components/ui/Alert';
import { TextField } from '@/components/ui/Field';
import type { MapBounds } from '@/lib/map/MapEngine';
import type { useAreaSelection } from './useAreaSelection';

export function MapAreaSelection({
  selection,
  hasArea,
  changed,
  opened,
  readViewport,
}: {
  selection: ReturnType<typeof useAreaSelection>;
  hasArea: boolean;
  changed: boolean;
  opened: boolean;
  readViewport: () => MapBounds | null;
}) {
  return (
    <details className="rounded border border-line p-3" data-area-draft-dirty={selection.dirty}>
      <summary className="cursor-pointer text-sm font-medium">Select a map area</summary>
      <div className="mt-3 space-y-3">
        <p className="text-xs text-muted">
          Select a WGS84 rectangle as a local map reference. Applying an area does not run research
          or upload geometry. Saving the map stores it in the view’s existing personal/team scope.
        </p>
        {hasArea && (
          <p className="text-sm">
            An area polygon is present. It remains unchanged until you apply a replacement rectangle
            or clear it.
          </p>
        )}
        {changed && (
          <p role="status" className="text-sm">
            Area selection changed. Save the map to create an immutable revision.
          </p>
        )}
        <div className="grid gap-3 sm:grid-cols-2">
          {(['west', 'south', 'east', 'north'] as const).map((field) => (
            <TextField
              key={field}
              label={`Area ${field}`}
              type="number"
              step="any"
              min={field === 'west' || field === 'east' ? -180 : -90}
              max={field === 'west' || field === 'east' ? 180 : 90}
              value={selection.draft[field]}
              onChange={(event) => selection.edit(field, event.target.value)}
            />
          ))}
        </div>
        <p className="text-xs text-muted">
          West greater than east crosses the antimeridian. Crossing rectangles are stored as
          canonical split polygons; wide numeric rectangles retain their specified span.
        </p>
        {selection.origin && <p className="text-xs text-muted">{selection.origin}</p>}
        {selection.picking && (
          <p role="status" className="text-sm">
            {selection.first
              ? `First corner: ${selection.first[0]}, ${selection.first[1]}. Choose the opposite corner.`
              : 'Choose two corners on the map. Numeric bounds are available as a keyboard alternative.'}
          </p>
        )}
        {selection.error && <Alert tone="error">{selection.error}</Alert>}
        {selection.dirty && (
          <p className="text-xs text-muted">
            Unapplied area draft. Review all four coordinates, then apply or discard it before
            saving the map.
          </p>
        )}
        <div className="flex flex-wrap gap-2">
          <Button
            variant="secondary"
            disabled={!opened}
            onClick={() => selection.viewport(readViewport)}
          >
            Use viewport envelope
          </Button>
          <Button
            variant="secondary"
            disabled={!opened}
            aria-pressed={selection.picking}
            onClick={selection.start}
          >
            Choose two map corners
          </Button>
          <Button
            variant="secondary"
            disabled={!selection.dirty || selection.picking}
            onClick={selection.apply}
          >
            Apply rectangle
          </Button>
          <Button variant="ghost" disabled={!selection.dirty} onClick={selection.cancel}>
            Discard area draft
          </Button>
          <Button variant="ghost" disabled={!hasArea} onClick={selection.clear}>
            Clear selected area
          </Button>
        </div>
      </div>
    </details>
  );
}

import { lazy, Suspense } from 'react';
import type { ComponentProps } from 'react';
import type EvidenceMapCanvas from './EvidenceMapCanvas';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';

const Canvas = lazy(() =>
  import('./EvidenceMapCanvas').catch(() => ({
    default: () => (
      <Alert tone="warning">
        The map renderer could not load. Use the evidence list or reload the page.
      </Alert>
    ),
  })),
);

export function ReportMapRenderer({
  opened,
  onOpened,
  onProjection,
  polar,
  canvas,
}: {
  opened: boolean;
  onOpened: (opened: boolean) => void;
  onProjection: (projection: 'globe' | 'mercator') => void;
  polar: number;
  canvas: ComponentProps<typeof EvidenceMapCanvas>;
}) {
  if (!opened)
    return (
      <div className="space-y-2">
        <p className="text-xs text-muted">
          Opening the map requests public basemap tiles from an external provider, which can
          disclose the viewed area and your network address. Evidence text is not sent to the tile
          provider.
        </p>
        <Button variant="secondary" onClick={() => onOpened(true)}>
          Open evidence map
        </Button>
      </div>
    );
  return (
    <>
      <div className="flex flex-wrap gap-2" aria-label="Evidence map projection">
        <Button
          variant="secondary"
          aria-pressed={canvas.projection === 'globe'}
          onClick={() => onProjection('globe')}
        >
          Globe
        </Button>
        <Button
          variant="secondary"
          aria-pressed={canvas.projection === 'mercator'}
          onClick={() => onProjection('mercator')}
        >
          Flat map
        </Button>
        <Button variant="ghost" onClick={() => onOpened(false)}>
          Close evidence map
        </Button>
      </div>
      {canvas.projection === 'mercator' && polar > 0 && (
        <Alert tone="warning">
          {polar} polar records cannot be displayed in Mercator. Use Globe or select them in the
          list; original coordinates are unchanged.
        </Alert>
      )}
      <Suspense fallback={<LoadingNote label="Loading saved evidence map" />}>
        <Canvas {...canvas} />
      </Suspense>
    </>
  );
}

import type { useMapWorkspaceTools } from './useMapWorkspaceTools';

/** Editing actions stay reachable while the inspector is collapsed. */
export function MapToolActivity({ tools }: { tools: ReturnType<typeof useMapWorkspaceTools> }) {
  const drawing = tools.research.drawing.picking
    ? tools.research.drawing
    : tools.drawing.picking
      ? tools.drawing
      : null;
  if (!drawing && !tools.rf.picking && !tools.measurement.picking) return null;
  return (
    <section
      aria-label="Active map tool"
      className="absolute bottom-24 left-1/2 z-30 max-w-[calc(100%-2rem)] -translate-x-1/2 rounded border border-cyan bg-ground px-3 py-2 text-xs text-cyan shadow-lg"
    >
      {drawing ? (
        <>
          <p role="status">
            {tools.research.drawing.picking ? 'Research boundary' : 'Drawing'} · {drawing.shape} ·{' '}
            {drawing.anchors.length} points
          </p>
          <div className="flex flex-wrap items-center gap-4">
            <button
              type="button"
              className="min-h-11 underline disabled:opacity-40"
              disabled={!drawing.canUndo}
              onClick={drawing.undo}
            >
              Undo
            </button>
            <button
              type="button"
              className="min-h-11 underline disabled:opacity-40"
              disabled={!drawing.canRedo}
              onClick={drawing.redo}
            >
              Redo
            </button>
            <button
              type="button"
              className="min-h-11 font-medium underline"
              onClick={() => drawing.setPicking(false)}
            >
              Finish drawing
            </button>
            <button type="button" className="min-h-11 underline" onClick={drawing.clear}>
              Discard sketch
            </button>
          </div>
        </>
      ) : tools.measurement.picking ? (
        <>
          <p role="status">Measuring · {tools.measurement.points.length} points</p>
          <div className="flex gap-4">
            <button
              type="button"
              className="min-h-11 underline"
              disabled={!tools.measurement.points.length}
              onClick={tools.measurement.undo}
            >
              Undo point
            </button>
            <button
              type="button"
              className="min-h-11 underline"
              onClick={() => tools.measurement.setPicking(false)}
            >
              Finish measuring
            </button>
          </div>
        </>
      ) : (
        <>
          <p role="status">
            {tools.rf.interaction === 'drag' ? 'Drag the marked' : 'Choose the'}{' '}
            {tools.rf.picking === 'origin' ? 'transmitter' : 'receiver'} on the map.
          </p>
          <button
            type="button"
            className="min-h-11 underline"
            onClick={() => tools.rf.setPicking(null)}
          >
            Cancel placement
          </button>
        </>
      )}
    </section>
  );
}

import type { DrawingWorkspace } from './useDrawingWorkspace';
import { useEffect, useRef } from 'react';
import { WorkspaceField } from '@/components/ui/WorkspaceField';
import { useWorkspaces, useWorkspaceSelection } from '@/lib/hooks/useWorkspaces';

export function DrawingStorageControls({ storage }: { storage: DrawingWorkspace['storage'] }) {
  const workspaces = useWorkspaces();
  const scope = useWorkspaceSelection(workspaces);
  const decision = useRef<HTMLElement>(null);
  useEffect(() => {
    if (storage.pendingLoad) decision.current?.focus();
  }, [storage.pendingLoad]);
  return (
    <section aria-label="Saved drawing collections" className="map-tool-section">
      <label className="map-tool-help">
        Collection title
        <input
          aria-label="Collection title"
          value={storage.title}
          maxLength={120}
          onChange={(event) => storage.setTitle(event.target.value)}
          className="map-tool-input w-full"
        />
      </label>
      <p className="map-tool-help">
        {storage.active
          ? `Saved in ${workspaces.label(storage.active.team_id)}. `
          : 'Choose who can access this collection. '}
        Saving updates the opened revision; conflicting edits are never overwritten.
      </p>
      {!storage.active && (
        <WorkspaceField
          workspaces={workspaces}
          value={scope.teamId}
          onChange={scope.select}
          disabled={storage.busy}
        />
      )}
      <div className="map-tool-actions">
        <button
          type="button"
          onClick={() => void storage.save(false, scope.teamId || undefined)}
          disabled={storage.busy || !storage.title.trim() || !scope.ready || storage.pendingEdits}
          className="map-tool-primary"
        >
          Save collection
        </button>
        {storage.active && (
          <button
            type="button"
            onClick={() => void storage.save(true)}
            disabled={storage.busy || storage.pendingEdits}
            className="map-tool-secondary"
          >
            Save a personal copy
          </button>
        )}
        <button
          type="button"
          onClick={() => void storage.browse()}
          disabled={storage.busy}
          className="map-tool-secondary"
        >
          Browse saved
        </button>
      </div>
      {storage.pendingEdits && (
        <p role="status" className="map-tool-notice">
          Add the sketch to the collection or apply its edits before saving. Clearing the temporary
          sketch discards those edits.
        </p>
      )}
      {storage.pendingLoad && (
        <section
          ref={decision}
          tabIndex={-1}
          aria-label="Unsaved drawing changes"
          className="map-tool-section"
        >
          <p role="alert">
            Opening another collection will replace your unsaved drawings and sketch.
          </p>
          <div className="map-tool-actions">
            <button
              type="button"
              className="map-tool-primary"
              disabled={
                storage.busy || storage.pendingEdits || !storage.title.trim() || !scope.ready
              }
              onClick={() => void storage.confirmLoad('save', scope.teamId || undefined)}
            >
              Save and open
            </button>
            <button
              type="button"
              className="map-tool-secondary"
              disabled={storage.busy}
              onClick={() => void storage.confirmLoad('discard')}
            >
              Discard and open
            </button>
            <button
              type="button"
              className="map-tool-text-button"
              disabled={storage.busy}
              onClick={storage.cancelLoad}
            >
              Cancel opening
            </button>
          </div>
          {storage.pendingEdits && (
            <p className="map-tool-help">
              Finish and add the sketch, or apply its edits, to enable Save and open.
            </p>
          )}
        </section>
      )}
      {storage.documents.map((item) => (
        <button
          key={item.id}
          type="button"
          disabled={storage.busy}
          onClick={() => void storage.load(item.id)}
          className="map-tool-secondary w-full"
        >
          Open {item.title} (revision {item.revision})
        </button>
      ))}
      {storage.hasMore && (
        <button
          type="button"
          disabled={storage.busy}
          onClick={() => void storage.loadMore()}
          className="map-tool-secondary w-full"
        >
          Load more collections
        </button>
      )}
      {storage.error && <p role="alert">{storage.error}</p>}
      {storage.notice && <p role="status">{storage.notice}</p>}
    </section>
  );
}

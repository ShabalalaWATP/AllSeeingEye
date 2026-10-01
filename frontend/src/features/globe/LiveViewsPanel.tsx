import { useState } from 'react';

import { WorkspaceField } from '@/components/ui/WorkspaceField';
import type { MapWorkspaceDocument } from '@/lib/api/mapWorkspace';
import { useWorkspaces, useWorkspaceSelection } from '@/lib/hooks/useWorkspaces';
import type { LiveViewControls } from './useLiveViewControls';
import type { LiveViewLibrary } from './useLiveViewLibrary';
import { VIEW_PARAM } from './useLiveViewOpening';

export function liveViewLink(id: string): string {
  return `${window.location.origin}/?${VIEW_PARAM}=${encodeURIComponent(id)}`;
}

/** Save the current layers, filters, time window, nation, projection and camera by name. */
export function LiveViewsPanel({
  library,
  controls,
  onOpen,
}: {
  library: LiveViewLibrary;
  controls: Pick<LiveViewControls, 'capture'>;
  onOpen: (id: string) => void;
}) {
  const workspaces = useWorkspaces();
  const scope = useWorkspaceSelection(workspaces);
  const [title, setTitle] = useState('');
  const [confirming, setConfirming] = useState<string | null>(null);
  const [copied, setCopied] = useState<string | null>(null);
  const { active, busy } = library;
  const canUpdate = active !== null && workspaces.canManage(active);
  const copy = (item: MapWorkspaceDocument) => {
    const link = liveViewLink(item.id);
    const written =
      'clipboard' in navigator
        ? navigator.clipboard.writeText(link)
        : Promise.reject(new Error('Clipboard unavailable.'));
    void written.then(
      () => setCopied(`Link to ${item.title} copied. It opens only for people who can see it.`),
      () => setCopied(`Copy this link: ${link}`),
    );
  };
  return (
    <section aria-label="Saved live views" className="map-tool-section">
      <p className="map-tool-help">
        A saved view keeps layer switches, filters, the time window, the nation filter, the
        projection and the camera. It never stores events and only opens when you choose it.
      </p>
      <label className="map-tool-help">
        View name
        <input
          aria-label="View name"
          value={title}
          maxLength={200}
          placeholder={active?.title ?? 'Baltic military aviation, 24 h'}
          onChange={(event) => setTitle(event.target.value)}
          className="map-tool-input w-full"
        />
      </label>
      <WorkspaceField
        workspaces={workspaces}
        value={scope.teamId}
        onChange={scope.select}
        disabled={busy}
      />
      <div className="map-tool-actions">
        <button
          type="button"
          className="map-tool-primary"
          disabled={busy || !title.trim() || !scope.ready}
          onClick={() => void library.save(controls.capture(), title, false, scope.teamId)}
        >
          Save as new view
        </button>
        {canUpdate && (
          <button
            type="button"
            className="map-tool-secondary"
            disabled={busy}
            onClick={() =>
              void library.save(controls.capture(), title.trim() || active.title, true)
            }
          >
            Update {active.title}
          </button>
        )}
        <button
          type="button"
          className="map-tool-text-button"
          disabled={busy}
          onClick={library.refresh}
        >
          Refresh list
        </button>
      </div>
      {library.items.length === 0 && !busy && <p className="map-tool-help">No saved views yet.</p>}
      <ul className="space-y-2" aria-label="Saved views">
        {library.items.map((item) => (
          <li key={item.id} className="rounded border border-line p-2">
            <p className="text-xs">
              <strong>{item.title}</strong>{' '}
              <span className="text-muted">
                {workspaces.label(item.team_id)} · revision {item.revision}
              </span>
            </p>
            <div className="map-tool-actions">
              <button
                type="button"
                className="map-tool-secondary"
                disabled={busy}
                aria-label={`Open ${item.title}`}
                onClick={() => {
                  library.select(item);
                  onOpen(item.id);
                }}
              >
                Open
              </button>
              <button
                type="button"
                className="map-tool-text-button"
                aria-label={`Copy link to ${item.title}`}
                onClick={() => copy(item)}
              >
                Copy link
              </button>
              {workspaces.canManage(item) &&
                (confirming === item.id ? (
                  <button
                    type="button"
                    className="map-tool-text-button"
                    disabled={busy}
                    onClick={() => {
                      setConfirming(null);
                      void library.remove(item);
                    }}
                  >
                    Confirm delete {item.title}
                  </button>
                ) : (
                  <button
                    type="button"
                    className="map-tool-text-button"
                    disabled={busy}
                    aria-label={`Delete ${item.title}`}
                    onClick={() => setConfirming(item.id)}
                  >
                    Delete
                  </button>
                ))}
            </div>
          </li>
        ))}
      </ul>
      {copied && <p role="status">{copied}</p>}
      {library.error && <p role="alert">{library.error}</p>}
      {library.notice && <p role="status">{library.notice}</p>}
    </section>
  );
}

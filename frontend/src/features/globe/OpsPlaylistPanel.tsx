import { useState } from 'react';

import { WorkspaceField } from '@/components/ui/WorkspaceField';
import { useWorkspaces, useWorkspaceSelection } from '@/lib/hooks/useWorkspaces';
import {
  MAX_CAPTION,
  MAX_DWELL_SECONDS,
  MAX_PLAYLIST_ENTRIES,
  MIN_DWELL_SECONDS,
} from '@/lib/liveViews/opsPlaylist';
import type { OpsPlaylistEditor } from './useOpsPlaylistEditor';

/** Choose what the wall screen cycles through. Entries are re-checked as they come round. */
export function OpsPlaylistPanel({
  editor,
  onPlay,
}: {
  editor: OpsPlaylistEditor;
  onPlay: (id: string) => void;
}) {
  const workspaces = useWorkspaces();
  const scope = useWorkspaceSelection(workspaces);
  const [choice, setChoice] = useState('');
  // Tied to one playlist, so choosing another never carries an open confirmation across.
  const [confirmingId, setConfirmingId] = useState<string | null>(null);
  const { active, busy, entries } = editor;
  const confirming = active !== null && confirmingId === active.id;
  if (confirmingId !== null && !confirming) setConfirmingId(null);
  const teamId = active ? active.team_id : scope.teamId || null;
  const options = editor.compatible(teamId);
  const label = (id: string) =>
    editor.sources.find((source) => source.id === id)?.label ?? 'Unavailable entry';
  const full = entries.length >= MAX_PLAYLIST_ENTRIES;
  return (
    <section aria-label="Ops room playlist" className="map-tool-section">
      <p className="map-tool-help">
        The ops room shows each saved view or saved area for its dwell time, with your caption.
        Entries must share the playlist&apos;s workspace. Anything deleted or no longer shared is
        skipped with a notice. Escape still leaves the ops room and alerts still show.
      </p>
      {editor.playlists.length > 0 && (
        <label className="map-tool-help">
          Saved playlists
          <select
            aria-label="Saved playlists"
            className="map-tool-input w-full"
            value={active?.id ?? ''}
            disabled={busy}
            onChange={(event) => {
              if (event.target.value) void editor.open(event.target.value);
              else editor.startNew();
            }}
          >
            <option value="">New playlist</option>
            {editor.playlists.map((item) => (
              <option key={item.id} value={item.id}>
                {item.title} ({workspaces.label(item.team_id)})
              </option>
            ))}
          </select>
        </label>
      )}
      <label className="map-tool-help">
        Playlist name
        <input
          aria-label="Playlist name"
          value={editor.title}
          maxLength={200}
          onChange={(event) => editor.setTitle(event.target.value)}
          className="map-tool-input w-full"
        />
      </label>
      {!active && (
        <WorkspaceField
          workspaces={workspaces}
          value={scope.teamId}
          onChange={scope.select}
          disabled={busy || entries.length > 0}
        />
      )}
      <ol className="space-y-2" aria-label="Playlist entries">
        {entries.map((entry, index) => {
          const position = String(index + 1);
          return (
            <li key={`${entry.id}-${position}`} className="rounded border border-line p-2 text-xs">
              <p>
                {position}. {label(entry.id)}
              </p>
              <label className="map-tool-help">
                Caption
                <input
                  aria-label={`Caption for entry ${position}`}
                  value={entry.caption}
                  maxLength={MAX_CAPTION}
                  onChange={(event) => editor.update(index, { caption: event.target.value })}
                  className="map-tool-input w-full"
                />
              </label>
              <label className="map-tool-help">
                Seconds on screen
                <input
                  aria-label={`Seconds for entry ${position}`}
                  type="number"
                  min={MIN_DWELL_SECONDS}
                  max={MAX_DWELL_SECONDS}
                  value={entry.dwell_text ?? entry.dwell_seconds}
                  onChange={(event) => editor.typeDwell(index, event.target.value)}
                  onBlur={() => editor.commitDwell(index)}
                  className="map-tool-input w-24"
                />
              </label>
              <div className="map-tool-actions">
                <button
                  type="button"
                  className="map-tool-text-button"
                  disabled={index === 0}
                  aria-label={`Move entry ${position} earlier`}
                  onClick={() => editor.move(index, -1)}
                >
                  Earlier
                </button>
                <button
                  type="button"
                  className="map-tool-text-button"
                  disabled={index === entries.length - 1}
                  aria-label={`Move entry ${position} later`}
                  onClick={() => editor.move(index, 1)}
                >
                  Later
                </button>
                <button
                  type="button"
                  className="map-tool-text-button"
                  aria-label={`Remove entry ${position}`}
                  onClick={() => editor.remove(index)}
                >
                  Remove
                </button>
              </div>
            </li>
          );
        })}
      </ol>
      <label className="map-tool-help">
        Add a saved view or area
        <select
          aria-label="Add a saved view or area"
          className="map-tool-input w-full"
          value={choice}
          disabled={busy || editor.loading || full}
          onChange={(event) => setChoice(event.target.value)}
        >
          <option value="">Choose</option>
          {options.map((source) => (
            <option key={source.id} value={source.id}>
              {source.label}
            </option>
          ))}
        </select>
      </label>
      <p className="map-tool-help">
        {full
          ? `A playlist holds up to ${String(MAX_PLAYLIST_ENTRIES)} entries.`
          : `${String(entries.length)} of ${String(MAX_PLAYLIST_ENTRIES)} entries.`}
      </p>
      <div className="map-tool-actions">
        <button
          type="button"
          className="map-tool-secondary"
          disabled={busy || !choice || full}
          onClick={() => {
            const source = options.find((item) => item.id === choice);
            if (source) editor.add(source);
            setChoice('');
          }}
        >
          Add to playlist
        </button>
        <button
          type="button"
          className="map-tool-primary"
          disabled={busy || entries.length === 0 || !editor.title.trim() || !scope.ready}
          onClick={() => void editor.save(active ? undefined : scope.teamId)}
        >
          Save playlist
        </button>
        {active && (
          <button
            type="button"
            className="map-tool-secondary"
            disabled={busy}
            onClick={() => onPlay(active.id)}
          >
            Play saved playlist in ops room
          </button>
        )}
        {active &&
          workspaces.canManage(active) &&
          (confirming ? (
            <>
              <button
                type="button"
                className="map-tool-text-button"
                disabled={busy}
                onClick={() => {
                  setConfirmingId(null);
                  void editor.destroy();
                }}
              >
                Confirm delete {active.title}
              </button>
              <button
                type="button"
                className="map-tool-text-button"
                disabled={busy}
                onClick={() => setConfirmingId(null)}
              >
                Cancel
              </button>
            </>
          ) : (
            <button
              type="button"
              className="map-tool-text-button"
              disabled={busy}
              onClick={() => setConfirmingId(active.id)}
            >
              Delete playlist
            </button>
          ))}
      </div>
      {editor.loadError && <p role="alert">{editor.loadError}</p>}
      {editor.error && <p role="alert">{editor.error}</p>}
      {editor.notice && <p role="status">{editor.notice}</p>}
    </section>
  );
}

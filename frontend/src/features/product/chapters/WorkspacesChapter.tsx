/**
 * Chapter 7: Specialist workspaces. A gallery of panels: on roomy screens vertical
 * scroll drives the track sideways while the chapter is pinned; elsewhere it is a
 * swipeable row. Previous and next buttons, and the arrow keys on the focusable
 * gallery, move one panel at a time and announce the position. A still story shows
 * the panels as an ordinary vertical list. Panels hold no controls, so focus moves
 * from the gallery to its buttons and on, in visual order.
 */
import type { CSSProperties } from 'react';

import { WORKSPACES, type Workspace } from '../content/platform';
import { ScrollChapter } from '../motion/ScrollChapter';
import { useHorizontalPin } from '../motion/useHorizontalPin';
import { useStoryMotion } from '../motion/useStoryMotion';
import { WorkspaceMedia } from './WorkspaceMedia';

import '../story-workspaces.css';

function WorkspaceCard({ workspace, number }: { workspace: Workspace; number: number }) {
  return (
    <article
      className="workspace-card"
      aria-labelledby={`workspace-${workspace.id}`}
      style={{ '--accent': workspace.accent } as CSSProperties}
    >
      <span className="workspace-number" aria-hidden="true">
        {String(number).padStart(2, '0')}
      </span>
      <h3 id={`workspace-${workspace.id}`}>{workspace.name}</h3>
      {workspace.media !== undefined ? <WorkspaceMedia media={workspace.media} /> : null}
      <p>{workspace.body}</p>
      <ul>
        {workspace.points.map((point) => (
          <li key={point}>{point}</li>
        ))}
      </ul>
      {workspace.limit !== undefined ? (
        <p className="workspace-limit">
          <strong>Limit</strong> {workspace.limit}
        </p>
      ) : null}
    </article>
  );
}

export function WorkspacesChapter({ panels = WORKSPACES }: { panels?: readonly Workspace[] }) {
  const { still } = useStoryMotion();
  const { trackRef, viewportRef, index, last, goTo, onProgress, onKeyDown } = useHorizontalPin(
    panels.length,
  );
  const carousel = !still;

  return (
    <ScrollChapter
      id="workspaces"
      label="Specialist workspaces"
      length={2.4}
      onProgress={onProgress}
      className="story-workspaces"
    >
      <div className="workspaces-head">
        <p className="story-eyebrow">07 · Go deeper</p>
        <h2 className="story-title">Specialist workspaces for specialist questions.</h2>
      </div>
      {/* The carousel region takes focus so the arrow keys can move it (WAI-ARIA APG). */}
      {/* eslint-disable-next-line jsx-a11y/no-static-element-interactions */}
      <div
        className="workspaces-gallery"
        role={carousel ? 'region' : undefined}
        aria-roledescription={carousel ? 'carousel' : undefined}
        aria-label={carousel ? 'Workspace gallery' : undefined}
        // eslint-disable-next-line jsx-a11y/no-noninteractive-tabindex -- Arrow keys move the gallery.
        tabIndex={carousel ? 0 : undefined}
        onKeyDown={carousel ? onKeyDown : undefined}
      >
        {carousel ? (
          <div className="workspaces-controls">
            <button
              type="button"
              aria-label="Previous workspace"
              disabled={index === 0}
              onClick={() => goTo(index - 1)}
            >
              <span aria-hidden="true">←</span>
            </button>
            <p className="workspaces-position" aria-live="polite" aria-atomic="true">
              Panel {index + 1} of {panels.length}
            </p>
            <button
              type="button"
              aria-label="Next workspace"
              disabled={index === last}
              onClick={() => goTo(index + 1)}
            >
              <span aria-hidden="true">→</span>
            </button>
          </div>
        ) : null}
        <div ref={viewportRef} className="workspaces-viewport">
          <div ref={trackRef} className="workspace-track" role={carousel ? undefined : 'list'}>
            {panels.map((workspace, position) => (
              <div
                key={workspace.id}
                className="workspace-slide"
                role={carousel ? 'group' : 'listitem'}
                aria-roledescription={carousel ? 'slide' : undefined}
                aria-label={carousel ? `${position + 1} of ${panels.length}` : undefined}
              >
                <WorkspaceCard workspace={workspace} number={position + 1} />
              </div>
            ))}
          </div>
        </div>
      </div>
    </ScrollChapter>
  );
}

/**
 * Chapter 7: Specialist workspaces. On wide screens vertical scroll drives a
 * horizontal gallery; the track offset is computed from measured widths on resize
 * and applied per frame as a transform. The cards hold no controls, so keyboard
 * scrolling moves the gallery and screen readers read every card in order. Small
 * screens get an ordinary swipeable row.
 */
import { useCallback, useEffect, useRef, type CSSProperties } from 'react';

import { WORKSPACES } from '../content/platform';
import { ScrollChapter } from '../motion/ScrollChapter';

export function WorkspacesChapter() {
  const trackRef = useRef<HTMLUListElement>(null);
  const travelRef = useRef(0);

  useEffect(() => {
    const track = trackRef.current;
    if (track === null) return undefined;
    const measure = () => {
      const viewport = track.parentElement?.clientWidth ?? window.innerWidth;
      travelRef.current = Math.max(0, track.scrollWidth - viewport);
    };
    measure();
    if (typeof ResizeObserver !== 'function') return undefined;
    const observer = new ResizeObserver(measure);
    observer.observe(track);
    if (track.parentElement !== null) observer.observe(track.parentElement);
    return () => observer.disconnect();
  }, []);

  const onProgress = useCallback((progress: number) => {
    const track = trackRef.current;
    if (track === null) return;
    const pinned = track.closest('[data-mode="pinned"]') !== null;
    track.style.transform = pinned
      ? `translate3d(${(-progress * travelRef.current).toFixed(1)}px,0,0)`
      : '';
  }, []);

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
      <div className="workspaces-viewport">
        <ul ref={trackRef} className="workspace-track">
          {WORKSPACES.map((workspace, index) => (
            <li key={workspace.id}>
              <article
                className="workspace-card"
                aria-labelledby={`workspace-${workspace.id}`}
                style={{ '--accent': workspace.accent } as CSSProperties}
              >
                <span className="workspace-number" aria-hidden="true">
                  {String(index + 1).padStart(2, '0')}
                </span>
                <h3 id={`workspace-${workspace.id}`}>{workspace.name}</h3>
                <p>{workspace.body}</p>
                <ul>
                  {workspace.points.map((point) => (
                    <li key={point}>{point}</li>
                  ))}
                </ul>
              </article>
            </li>
          ))}
        </ul>
      </div>
    </ScrollChapter>
  );
}

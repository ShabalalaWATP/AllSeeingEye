/**
 * Chapter 1: Observe. A pinned globe reveals every map layer in the app's own order,
 * one per scroll beat, while the list beside it explains the layer and the filters it
 * offers. The final beat turns the Earth towards the Red Sea, where the Ask chapter's
 * question begins.
 */
import { useCallback, useRef, useState, type CSSProperties } from 'react';

import { LAYER_STORIES, LIVE_LAYER_COUNT, STORY_LAYERS } from '../content/observe';
import { segment } from '../motion/scrollScheduler';
import { ScrollChapter } from '../motion/ScrollChapter';
import { GlobeCanvas, type GlobeControls } from '../scenes/GlobeCanvas';

const STEPS = STORY_LAYERS.length + 1;
const LAYER_SPAN = STORY_LAYERS.length / STEPS;

export function ObserveChapter() {
  const controls = useRef<GlobeControls>({ revealed: 0, active: 0, focus: 0 });
  const [active, setActive] = useState(0);

  const onProgress = useCallback((progress: number) => {
    const layerProgress = segment(progress, 0, LAYER_SPAN);
    controls.current.revealed = 0.6 + layerProgress * STORY_LAYERS.length;
    controls.current.active = Math.min(
      STORY_LAYERS.length - 1,
      Math.floor(layerProgress * STORY_LAYERS.length),
    );
    controls.current.focus = segment(progress, LAYER_SPAN, 1);
  }, []);
  const onStep = useCallback(
    (step: number) => setActive(Math.min(step, STORY_LAYERS.length - 1)),
    [],
  );

  return (
    <ScrollChapter
      id="observe"
      label="Observe"
      length={STEPS * 0.32}
      pinNarrow
      steps={STEPS}
      onStep={onStep}
      onProgress={onProgress}
      className="story-observe"
    >
      <div className="observe-globe">
        <GlobeCanvas
          controls={controls}
          label="An illustrative globe showing each map layer appear in turn. Synthetic data."
        />
        <p className="story-illustrative">Illustrative data</p>
      </div>
      <div className="observe-copy">
        <p className="story-eyebrow">01 · Observe</p>
        <h2 className="story-title">One picture of a noisy world.</h2>
        <p className="story-lead">
          {LIVE_LAYER_COUNT} live layers and {STORY_LAYERS.length - LIVE_LAYER_COUNT} reference
          layers on a 3D globe or flat map, each with its own filters and source details.
        </p>
        <ol className="layer-list" style={{ '--active': active } as CSSProperties}>
          {STORY_LAYERS.map((layer, index) => {
            const story = LAYER_STORIES[layer.id];
            const state = index === active ? 'active' : index < active ? 'seen' : 'next';
            return (
              <li key={layer.id} className="layer-row" data-state={state}>
                <span
                  className="layer-dot"
                  style={{ background: story?.colour }}
                  aria-hidden="true"
                />
                <span className="layer-label">
                  {layer.label}
                  {index === LIVE_LAYER_COUNT ? (
                    <span className="layer-kind">Reference</span>
                  ) : null}
                </span>
                <div className="layer-detail">
                  <p>{layer.description}</p>
                  {story !== undefined && (
                    <ul className="chip-row" aria-label={`${layer.label} filters`}>
                      {story.filters.map((filter) => (
                        <li key={filter} className="chip">
                          {filter}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </li>
            );
          })}
        </ol>
      </div>
    </ScrollChapter>
  );
}

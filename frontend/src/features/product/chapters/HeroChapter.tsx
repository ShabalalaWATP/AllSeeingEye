/**
 * Chapter 0: the Eye opens. The real React Bits Evil Eye brand mark fills the stage,
 * wakes on arrival and, on a fine pointer, watches the cursor anywhere on the page;
 * as the reader scrolls it grows and dissolves into the globe that follows. The
 * headline is ordinary text and remains available independently of WebGL.
 */
import { useSyncExternalStore } from 'react';
import { Link } from 'react-router';

import EvilEye from '@/components/brand/EvilEyeSurface';

import { CountUp } from '../motion/CountUp';
import { ScrollChapter } from '../motion/ScrollChapter';
import { useStoryMotion } from '../motion/useStoryMotion';
import { SOURCE_TOTAL, SOURCE_TOPICS } from '../content/sources';
import { STORY_LAYERS } from '../content/observe';

const STATS = [
  { value: STORY_LAYERS.length, suffix: '', label: 'map layers' },
  { value: Math.floor(SOURCE_TOTAL / 100) * 100, suffix: '+', label: 'catalogued sources' },
  { value: SOURCE_TOPICS.length, suffix: '', label: 'intelligence topics' },
  { value: 7, suffix: '', label: 'probability bands' },
];

/**
 * Unpinned, the hero is already in view at load (half way through its pass), so the
 * Eye's dissolve plays over the second half, as the hero leaves the screen.
 */
const HERO_PASS = [0.5, 1] as const;

const FINE_POINTER = '(hover: hover) and (pointer: fine)';

function subscribePointer(onChange: () => void): () => void {
  if (typeof window.matchMedia !== 'function') return () => undefined;
  const query = window.matchMedia(FINE_POINTER);
  query.addEventListener('change', onChange);
  return () => query.removeEventListener('change', onChange);
}

function readFinePointer(): boolean {
  return typeof window.matchMedia === 'function' && window.matchMedia(FINE_POINTER).matches;
}

export function HeroChapter() {
  const { still, idle } = useStoryMotion();
  const finePointer = useSyncExternalStore(subscribePointer, readFinePointer, () => false);
  const follow = finePointer && !still;
  return (
    <ScrollChapter
      id="top"
      label="The All Seeing Eye"
      length={0.9}
      passWindow={HERO_PASS}
      className="story-hero"
    >
      <div className="hero-grid" aria-hidden="true" />
      <div className="hero-eye" aria-hidden="true">
        <div className="hero-eye-wake">
          <EvilEye
            deferUntilVisible
            workerRendering
            backgroundColor="#060606"
            scale={0.95}
            maxFps={still ? 1 : 30}
            flameSpeed={still ? 0 : 1}
            pupilFollow={follow ? 1 : 0}
            pointerScope="page"
            saveDataFallback
            paused={idle}
            fallbackSizes="(max-width: 600px) 320px, 512px"
            fallbackPriority="high"
          />
        </div>
      </div>
      <div className="hero-copy">
        <p className="story-eyebrow">Open-source intelligence · self-hosted</p>
        <h1 className="hero-title">
          The All Seeing Eye<span aria-hidden="true">.</span>
        </h1>
        <p className="hero-lead">
          Watch the world&rsquo;s public signals on a living globe, ask a bounded question and get
          an assessment that shows the selected evidence, grades and doubts behind each judgement.
          On your own infrastructure, with the AI provider you choose.
        </p>
        <div className="hero-actions">
          <Link className="story-button story-button-primary" to="#contact">
            Talk to us
          </Link>
          <a className="story-button" href="#observe">
            See how it works
          </a>
        </div>
        <ul className="hero-stats" aria-label="At a glance">
          {STATS.map((stat) => (
            <li key={stat.label}>
              <strong>
                <CountUp value={stat.value} suffix={stat.suffix} />
              </strong>
              <span>{stat.label}</span>
            </li>
          ))}
        </ul>
      </div>
      <p className="hero-cue" aria-hidden="true">
        Scroll
        <span />
      </p>
    </ScrollChapter>
  );
}

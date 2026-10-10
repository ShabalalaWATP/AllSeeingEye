/**
 * Chapter 0: the Eye opens. The real React Bits Evil Eye brand mark fills the stage;
 * as the reader scrolls it grows and dissolves into the globe that follows. The
 * headline is ordinary text and remains available independently of WebGL.
 */
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

export function HeroChapter() {
  const { still, idle } = useStoryMotion();
  return (
    <ScrollChapter
      id="top"
      label="The All Seeing Eye"
      length={0.9}
      pinNarrow
      className="story-hero"
    >
      <div className="hero-grid" aria-hidden="true" />
      <div className="hero-eye" aria-hidden="true">
        <EvilEye
          deferUntilVisible
          workerRendering
          backgroundColor="#060606"
          scale={0.95}
          maxFps={still ? 1 : 30}
          flameSpeed={still ? 0 : 1}
          pupilFollow={still ? 0 : 1}
          paused={idle}
          fallbackSizes="(max-width: 600px) 320px, 512px"
          fallbackPriority="high"
        />
      </div>
      <div className="hero-copy">
        <p className="story-eyebrow">Open-source intelligence · self-hosted</p>
        <h1 className="hero-title">
          The All Seeing Eye<span aria-hidden="true">.</span>
        </h1>
        <p className="hero-lead">
          Watch the world&rsquo;s public signals on a living globe, ask a bounded question and get
          an assessment that shows every source, grade and doubt behind it. On your own
          infrastructure, with the AI provider you choose.
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

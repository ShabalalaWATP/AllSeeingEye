/**
 * Chapter 2: Sources. Eleven topic nodes fly in from the edge and settle into orbit
 * around the Eye as the reader scrolls, each sized by its catalogue count, while the
 * list beside them gives the counts and representative providers.
 */
import type { CSSProperties } from 'react';

import {
  COLLECTION_MODES,
  ON_DEMAND_TOTAL,
  SCHEDULED_TOTAL,
  SOURCE_CAVEAT,
  SOURCE_TOPICS,
  SOURCE_TOTAL,
} from '../content/sources';
import { CountUp } from '../motion/CountUp';
import { Reveal } from '../motion/Reveal';
import { ScrollChapter } from '../motion/ScrollChapter';

const MAX = Math.max(...SOURCE_TOPICS.map((topic) => topic.scheduled + topic.onDemand));

function nodeStyle(index: number, count: number): CSSProperties {
  const angle = (index / SOURCE_TOPICS.length) * Math.PI * 2 - Math.PI / 2;
  const ring = index % 2 === 0 ? 38 : 30;
  return {
    '--x': `${50 + Math.cos(angle) * ring}%`,
    '--y': `${50 + Math.sin(angle) * ring}%`,
    '--from-x': `${50 + Math.cos(angle) * 90}%`,
    '--from-y': `${50 + Math.sin(angle) * 90}%`,
    '--size': `${18 + Math.sqrt(count / MAX) * 40}px`,
    '--i': index,
  } as CSSProperties;
}

export function SourcesChapter() {
  return (
    <ScrollChapter id="sources" label="Sources" length={1.6} pin={false} className="story-sources">
      <div className="sources-orbit" aria-hidden="true">
        <div className="orbit-ring orbit-ring-outer" />
        <div className="orbit-ring orbit-ring-inner" />
        <div className="orbit-core">
          <strong>{SOURCE_TOTAL}</strong>
          <span>sources</span>
        </div>
        {SOURCE_TOPICS.map((topic, index) => {
          const count = topic.scheduled + topic.onDemand;
          return (
            <div
              key={topic.id}
              className="orbit-node"
              style={{ ...nodeStyle(index, count), '--colour': topic.colour } as CSSProperties}
            >
              <span className="orbit-dot" />
              <span className="orbit-label">{topic.label}</span>
            </div>
          );
        })}
      </div>
      <div className="sources-copy">
        <p className="story-eyebrow">02 · Sources</p>
        <h2 className="story-title">Hundreds of sources. Every one named.</h2>
        <p className="story-lead">
          <CountUp value={SCHEDULED_TOTAL} /> scheduled feeds and{' '}
          <CountUp value={ON_DEMAND_TOTAL} /> on-demand research connectors across eleven topics,
          from seismology to sanctions. Each record keeps its source, licence notes and collection
          time.
        </p>
        <ul className="topic-list">
          {SOURCE_TOPICS.map((topic, index) => {
            const count = topic.scheduled + topic.onDemand;
            return (
              <Reveal as="li" key={topic.id} order={index % 6} className="topic-row">
                <span
                  className="topic-bar"
                  style={{ '--share': count / MAX, '--colour': topic.colour } as CSSProperties}
                  aria-hidden="true"
                />
                <span className="topic-name">{topic.label}</span>
                <span className="topic-count">{count}</span>
                <span className="topic-examples">{topic.examples.join(' · ')}</span>
              </Reveal>
            );
          })}
        </ul>
        <ul className="mode-grid" aria-label="How sources are collected">
          {COLLECTION_MODES.map((mode, index) => (
            <Reveal as="li" key={mode.title} order={index} className="mode-card">
              <h3>{mode.title}</h3>
              <p>{mode.body}</p>
            </Reveal>
          ))}
        </ul>
        <p className="story-footnote">{SOURCE_CAVEAT}</p>
      </div>
    </ScrollChapter>
  );
}

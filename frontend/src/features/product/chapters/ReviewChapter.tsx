/**
 * Chapter 6: Review. A timeline slides past as the reader scrolls, showing one
 * assessment living on: follow-ups, subscription editions, an alert, a new version
 * and a resolved forecast. Alerts arrive on a phone; exports flip into a stack.
 */
import type { CSSProperties } from 'react';

import { ALERT_CHANNELS, EXPORTS, REVIEW_TIMELINE, WATCH_TYPES } from '../content/platform';
import { Reveal } from '../motion/Reveal';
import { ScrollChapter } from '../motion/ScrollChapter';

export function ReviewChapter() {
  return (
    <>
      <ScrollChapter id="review" label="Review" length={2} className="story-review">
        <div className="review-head">
          <p className="story-eyebrow">06 · Review</p>
          <h2 className="story-title">An assessment is the start of the work, not the end.</h2>
          <p className="story-lead">
            Saved research keeps its evidence frozen, its versions comparable and its forecasts
            accountable, while watches keep collecting in the background.
          </p>
        </div>
        <ol className="timeline" style={{ '--count': REVIEW_TIMELINE.length } as CSSProperties}>
          {REVIEW_TIMELINE.map((beat, index) => (
            <li
              key={beat.title}
              className="timeline-beat"
              style={{ '--i': index } as CSSProperties}
            >
              <span className="timeline-when">{beat.when}</span>
              <h3>{beat.title}</h3>
              <p>{beat.body}</p>
            </li>
          ))}
        </ol>
      </ScrollChapter>
      <section
        className="story-chapter story-review-more"
        aria-label="Watching, alerts and exports"
      >
        <div className="review-grid story-wrap">
          <Reveal className="review-panel">
            <h3>Six ways to keep watching</h3>
            <ul className="chip-row">
              {WATCH_TYPES.map((type) => (
                <li key={type} className="chip">
                  {type}
                </li>
              ))}
            </ul>
          </Reveal>
          <Reveal className="phone">
            <div className="phone-notch" aria-hidden="true" />
            <h3 className="sr-only">Alert delivery channels</h3>
            <ul>
              {ALERT_CHANNELS.map((channel, index) => (
                <li key={channel.label} className="toast" style={{ '--i': index } as CSSProperties}>
                  <strong>{channel.label}</strong>
                  <span>{channel.detail}</span>
                </li>
              ))}
            </ul>
          </Reveal>
          <Reveal className="review-panel">
            <h3>Take it anywhere</h3>
            <ul className="export-grid">
              {EXPORTS.map((item, index) => (
                <li
                  key={item.format}
                  className="export-card"
                  style={{ '--i': index } as CSSProperties}
                >
                  <strong>{item.format}</strong>
                  <span>{item.detail}</span>
                </li>
              ))}
            </ul>
          </Reveal>
        </div>
      </section>
    </>
  );
}

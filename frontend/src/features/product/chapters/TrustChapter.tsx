/**
 * Chapter 8: Trust and control. Four security layers separate in an exploded view as
 * the reader scrolls, each naming its controls. The honest limits that follow are
 * deliberately plain and unanimated.
 */
import type { CSSProperties } from 'react';

import { AI_CHOICES, ENGINEERING, LIMITS_TEXT, TRUST_LAYERS } from '../content/platform';
import { Reveal } from '../motion/Reveal';
import { ScrollChapter } from '../motion/ScrollChapter';

export function TrustChapter() {
  return (
    <>
      <ScrollChapter id="trust" label="Trust and control" length={1.6} className="story-trust">
        <div className="trust-copy">
          <p className="story-eyebrow">08 · Trust and control</p>
          <h2 className="story-title">Your server. Your model. Your rules.</h2>
          <p className="story-lead">
            The All Seeing Eye runs on infrastructure you control, talks to the AI provider you
            choose and treats every byte from the internet, every feed item and every model response
            as untrusted.
          </p>
        </div>
        <ol className="trust-stack" aria-label="Security layers">
          {TRUST_LAYERS.map((layer, index) => (
            <li key={layer.id} className="trust-layer" style={{ '--i': index } as CSSProperties}>
              <h3>{layer.name}</h3>
              <ul>
                {layer.controls.map((control) => (
                  <li key={control}>{control}</li>
                ))}
              </ul>
            </li>
          ))}
        </ol>
      </ScrollChapter>
      <section className="story-chapter story-honest" aria-label="Choices and limits">
        <div className="story-wrap honest-grid">
          <Reveal className="honest-panel">
            <h3>Bring your own AI</h3>
            <ul className="tick-list">
              {AI_CHOICES.map((choice) => (
                <li key={choice}>{choice}</li>
              ))}
            </ul>
          </Reveal>
          <Reveal order={1} className="honest-panel">
            <h3>Engineered with care</h3>
            <ul className="tick-list">
              {ENGINEERING.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
            <p className="story-footnote">Practices, not a security certification.</p>
          </Reveal>
          <div className="honest-panel honest-limits">
            <h3>What it will not pretend</h3>
            <ul>
              {LIMITS_TEXT.map((limit) => (
                <li key={limit}>{limit}</li>
              ))}
            </ul>
          </div>
        </div>
      </section>
    </>
  );
}

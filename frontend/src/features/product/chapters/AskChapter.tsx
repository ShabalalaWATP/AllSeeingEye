/**
 * Chapter 3: Ask. The example question types itself as the reader scrolls, then its
 * scope chips snap in and the depth selector steps from Basic to Advanced. Typing is
 * written straight into a text node, so scrolling does not re-render React.
 */
import { useCallback, useRef, useState, type CSSProperties } from 'react';

import { ASK_FEATURES, DEPTHS, EXAMPLE_QUESTION, SCOPE_CHIPS } from '../content/research';
import { segment } from '../motion/scrollScheduler';
import { Reveal } from '../motion/Reveal';
import { ScrollChapter } from '../motion/ScrollChapter';
import { useStoryMotion } from '../motion/useStoryMotion';

export function AskChapter() {
  const { still } = useStoryMotion();
  const typedRef = useRef<HTMLSpanElement>(null);
  const [depth, setDepth] = useState(still ? DEPTHS.length - 1 : 0);

  const onProgress = useCallback((progress: number) => {
    const typed = typedRef.current;
    if (typed === null) return;
    const count = Math.round(segment(progress, 0.05, 0.45) * EXAMPLE_QUESTION.length);
    typed.textContent = EXAMPLE_QUESTION.slice(0, count);
  }, []);
  const onStep = useCallback(
    (step: number) => setDepth(Math.max(0, Math.min(DEPTHS.length - 1, step - 5))),
    [],
  );

  return (
    <ScrollChapter
      id="ask"
      label="Ask"
      length={1.8}
      steps={8}
      onStep={onStep}
      onProgress={onProgress}
      className="story-ask"
    >
      <div className="ask-copy">
        <p className="story-eyebrow">03 · Ask</p>
        <h2 className="story-title">Start with a question, not a search box.</h2>
        <p className="story-lead">
          Every run has an explicit scope: places, dates, languages, sources, a report template and
          a depth. Scope is what keeps the collection honest and the assessment checkable.
        </p>
        <ul className="tick-list">
          {ASK_FEATURES.map((feature, index) => (
            <Reveal as="li" key={feature} order={index}>
              {feature}
            </Reveal>
          ))}
        </ul>
      </div>
      <div className="ask-console" aria-label="Example research request">
        <div className="console-bar" aria-hidden="true">
          <span />
          <span />
          <span />
          <em>New research</em>
        </div>
        <p className="console-label">Question</p>
        <p className="console-question">
          <span className="sr-only">{EXAMPLE_QUESTION}</span>
          <span aria-hidden="true">
            <span ref={typedRef}>{still ? EXAMPLE_QUESTION : ''}</span>
            <span className="console-caret" />
          </span>
        </p>
        <p className="console-label">Scope</p>
        <ul className="scope-chips">
          {SCOPE_CHIPS.map((chip, index) => (
            <li key={chip.label} className="scope-chip" style={{ '--i': index } as CSSProperties}>
              <span>{chip.label}</span>
              {chip.value}
            </li>
          ))}
        </ul>
        <p className="console-label">Depth</p>
        <ul className="depth-select">
          {DEPTHS.map((option, index) => (
            <li key={option.name} data-selected={index === depth ? 'true' : 'false'}>
              <strong>{option.name}</strong>
              <span>{option.words}</span>
              <span>{option.evidence} evidence items</span>
            </li>
          ))}
        </ul>
      </div>
    </ScrollChapter>
  );
}

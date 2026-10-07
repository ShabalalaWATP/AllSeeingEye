/**
 * Chapter 4: Collect. Graded evidence cards arrive one by one from different
 * directions as connectors return; the collection gap stays visibly empty. Card
 * timing is pure CSS driven by the chapter's --progress value.
 */
import type { CSSProperties } from 'react';

import { EVIDENCE, GRADING } from '../content/research';
import { Reveal } from '../motion/Reveal';
import { ScrollChapter } from '../motion/ScrollChapter';

const ORIGINS = [
  [-60, -40],
  [70, -30],
  [-80, 20],
  [60, 40],
  [-30, 60],
  [40, -60],
] as const;

function origin(index: number): readonly [number, number] {
  return ORIGINS[index % ORIGINS.length] ?? [0, 40];
}

export function CollectChapter() {
  return (
    <ScrollChapter id="collect" label="Collect" length={1.6} className="story-collect">
      <div className="collect-copy">
        <p className="story-eyebrow">04 · Collect</p>
        <h2 className="story-title">Evidence with a receipt, and gaps you can see.</h2>
        <p className="story-lead">
          Connectors fan out across the scope. Each record comes back with its source, a grade and a
          collection receipt, and anything the run could not find is recorded as a gap rather than
          papered over.
        </p>
        <Reveal className="grade-legend">
          <p>
            <strong>{GRADING.reliability}</strong>
            <span>{GRADING.credibility}</span>
          </p>
          <p className="story-footnote">{GRADING.note}</p>
        </Reveal>
      </div>
      <ol className="evidence-stack" aria-label="Example evidence collected for the question">
        {EVIDENCE.map((card, index) => (
          <li
            key={card.id}
            className="evidence-card"
            data-gap={card.gap ? 'true' : 'false'}
            style={
              {
                '--i': index,
                '--dx': `${origin(index)[0]}vw`,
                '--dy': `${origin(index)[1]}vh`,
              } as CSSProperties
            }
          >
            <span className="evidence-family">{card.family}</span>
            <span className="evidence-title">{card.title}</span>
            <span className="evidence-meta">
              <span
                className="evidence-grade"
                aria-label={card.gap ? 'Collection gap' : `Grade ${card.grade}`}
              >
                {card.grade}
              </span>
              <span>{card.gap ? 'Gap recorded' : `Collected ${card.collected}`}</span>
            </span>
          </li>
        ))}
      </ol>
    </ScrollChapter>
  );
}

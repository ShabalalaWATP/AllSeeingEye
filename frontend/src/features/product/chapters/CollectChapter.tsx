/**
 * Chapter 4: Collect. Connector arcs fan out from the scope, then graded evidence
 * cards arrive one by one from different directions, each with its receipt; the
 * collection gap stays visibly empty. Card and arc timing is pure CSS driven by the
 * chapter's --progress value; arc shapes are measured only on mount and resize.
 */
import { useRef, type CSSProperties } from 'react';

import { EVIDENCE, GRADING, SHARED_ORIGIN } from '../content/research';
import { DrawPath } from '../motion/DrawPath';
import { Reveal } from '../motion/Reveal';
import { ScrollChapter } from '../motion/ScrollChapter';
import { useFanPaths } from '../motion/useFanPaths';

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
  const arcsRef = useRef<SVGSVGElement>(null);
  const stackRef = useRef<HTMLOListElement>(null);
  const fan = useFanPaths(arcsRef, stackRef);

  return (
    <ScrollChapter id="collect" label="Collect" length={1.6} className="story-collect">
      <div className="collect-copy">
        <p className="story-eyebrow">04 · Collect</p>
        <h2 className="story-title">Evidence with a receipt, and gaps you can see.</h2>
        <p className="story-lead">
          Connectors fan out across the scope. Each record comes back with its source and a grade.
          Collection receipts record which providers ran, including empty and unavailable ones, and
          requirements without enough support stay visible as gaps rather than papered over.
        </p>
        <p className="story-lead">{SHARED_ORIGIN}</p>
        <Reveal className="grade-legend">
          <p>
            <strong>{GRADING.reliability}</strong>
            <span>{GRADING.credibility}</span>
          </p>
          <p className="story-footnote">{GRADING.note}</p>
        </Reveal>
      </div>
      <div className="collect-stage">
        <svg
          ref={arcsRef}
          className="collect-arcs"
          height={fan.height || undefined}
          viewBox={fan.width > 0 ? `0 0 ${fan.width} ${fan.height}` : undefined}
          aria-hidden="true"
          focusable="false"
        >
          {fan.paths.map((d, index) => (
            <DrawPath
              key={EVIDENCE[index]?.id ?? index}
              d={d}
              start={0.02 + index * 0.02}
              rate={6}
            />
          ))}
          <circle className="collect-scope" cx="0" cy={fan.height / 2} r="4" />
        </svg>
        <ol
          ref={stackRef}
          className="evidence-stack"
          aria-label="Example evidence collected for the question"
        >
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
                <span className="evidence-receipt">Receipt {card.receipt}</span>
              </span>
            </li>
          ))}
        </ol>
        <p className="story-footnote">
          Illustrative evidence: example sources, grades and receipts.
        </p>
      </div>
    </ScrollChapter>
  );
}

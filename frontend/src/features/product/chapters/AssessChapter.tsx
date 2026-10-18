/**
 * Chapter 5: Assess. Judgements write themselves into the report, citation threads
 * draw back to the evidence they rest on, and a challenge sweep marks one judgement
 * as contested before the alternative explanation appears; a closing beat shows the
 * report living on as versions and follow-ups. All drawing is CSS driven by
 * --progress; connector shapes are measured only on resize.
 */
import { useRef, type CSSProperties } from 'react';

import {
  ALTERNATIVE,
  ASSESS_CHECKS,
  EVIDENCE,
  JUDGEMENTS,
  PHIA_BANDS,
  REPORT_HEADER,
  REPORT_NEXT,
} from '../content/research';
import { DrawPath } from '../motion/DrawPath';
import { useConnectorPaths } from '../motion/useConnectorPaths';
import { Reveal } from '../motion/Reveal';
import { ScrollChapter } from '../motion/ScrollChapter';

const PAIRS = JUDGEMENTS.flatMap((judgement) =>
  judgement.cites.map((cite) => [`${judgement.id}-${cite}`, cite] as const),
);
const CITED = EVIDENCE.filter((card) => !card.gap);

export function AssessChapter() {
  const stageRef = useRef<HTMLDivElement>(null);
  const { connectors, width, height } = useConnectorPaths(stageRef, PAIRS);

  return (
    <>
      <ScrollChapter id="assess" label="Assess" length={2.2} className="story-assess">
        <div className="assess-head">
          <p className="story-eyebrow">05 · Assess</p>
          <h2 className="story-title">Judgements you can trace, challenge and defend.</h2>
        </div>
        <div className="assess-stage" ref={stageRef}>
          <ul className="assess-evidence" aria-label="Evidence cited">
            {CITED.map((card) => (
              <li key={card.id} data-to={card.id} className="mini-evidence">
                <span className="evidence-grade">{card.grade}</span>
                {card.title}
              </li>
            ))}
          </ul>
          <svg className="assess-threads" width={width} height={height} aria-hidden="true">
            {connectors.map((connector, index) => (
              <DrawPath key={connector.key} d={connector.d} start={0.15 + index / 16} rate={4} />
            ))}
          </svg>
          <article className="assess-report" aria-label="Example assessment">
            <header>
              <span className="report-status">Ready</span>
              <h3>{REPORT_HEADER.title}</h3>
              <p>{REPORT_HEADER.summary}</p>
              <p className="report-model">{REPORT_HEADER.model}</p>
            </header>
            <ol>
              {JUDGEMENTS.map((judgement, index) => (
                <li
                  key={judgement.id}
                  className="judgement"
                  data-challenged={judgement.challenged ? 'true' : 'false'}
                  style={{ '--i': index } as CSSProperties}
                >
                  <span className="judgement-band">
                    {judgement.likelihood} · {judgement.confidence} confidence
                  </span>
                  <p>
                    {judgement.text}{' '}
                    {judgement.cites.map((cite) => (
                      <sup key={cite} data-from={`${judgement.id}-${cite}`} className="cite">
                        [{EVIDENCE.findIndex((card) => card.id === cite) + 1}]
                      </sup>
                    ))}
                  </p>
                  {judgement.challenged ? (
                    <p className="challenge-note">Challenged: confidence held at moderate.</p>
                  ) : null}
                </li>
              ))}
            </ol>
            <p className="alternative">{ALTERNATIVE}</p>
            <ul className="report-next" aria-label="What happens next">
              {REPORT_NEXT.map((step, index) => (
                <li key={step} style={{ '--i': index } as CSSProperties}>
                  {step}
                </li>
              ))}
            </ul>
          </article>
        </div>
        <p className="story-footnote">
          Illustrative report. It is static text, never generated here.
        </p>
      </ScrollChapter>
      <section className="story-chapter story-assess-more" aria-label="Analytic standards">
        <div className="assess-foot story-wrap">
          <div className="yardstick" aria-label="PHIA probability yardstick">
            {PHIA_BANDS.map((band, index) => (
              <span key={band} style={{ '--i': index } as CSSProperties}>
                {band}
              </span>
            ))}
          </div>
          <ul className="tick-list tick-list-columns">
            {ASSESS_CHECKS.map((check, index) => (
              <Reveal as="li" key={check} order={index}>
                {check}
              </Reveal>
            ))}
          </ul>
        </div>
      </section>
    </>
  );
}

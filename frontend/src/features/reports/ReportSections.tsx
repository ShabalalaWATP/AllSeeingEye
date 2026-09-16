import type { ReactNode } from 'react';

import type { DevilsAdvocacy, Direction, ReportBody } from '@/lib/api/reports';
import { probabilityTerm } from '@/lib/doctrine';
import type { ReportAssessment } from '@/lib/api/reportAssessment';

import { Labels } from './EvidenceLinks';
import type { CitationChecks } from '@/lib/api/reportResearch';
export { EvidenceAnnex } from './EvidenceAnnex';

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section aria-label={title} className="report-reader-section">
      <h2>{title}</h2>
      {children}
    </section>
  );
}

const BULLETS = 'mt-3 list-disc space-y-2 pl-5 marker:text-[color:var(--paper-accent-soft)]';

/** What an Ask the Eye question became: the requirement it serves, broken into SIRs and EEIs. */
export function DirectionView({ direction }: { direction: Direction | null }) {
  if (direction === null) return null;
  const rows = [
    ['PIR-1', direction.pir],
    ...direction.sirs.map((text, index) => [`SIR-${String(index + 1)}`, text]),
    ...direction.eeis.map((text, index) => [`EEI-${String(index + 1)}`, text]),
  ];
  return (
    <Section title="Direction">
      <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-3 gap-y-2 text-sm">
        {rows.map(([id, text]) => (
          <div key={id} className="contents">
            <dt className="font-mono text-xs text-[color:var(--paper-ink-soft)]">{id}</dt>
            <dd>{text}</dd>
          </div>
        ))}
      </dl>
      {direction.search_terms.length > 0 && (
        <p className="report-reader-note">Search terms: {direction.search_terms.join(', ')}</p>
      )}
    </Section>
  );
}

/** The contrarian view of the top judgement, and what it did to the confidence rating. */
export function AdvocacyView({ advocacy }: { advocacy: DevilsAdvocacy | null }) {
  if (advocacy === null) return null;
  const lowered = advocacy.confidence_before !== null && advocacy.confidence_after !== null;
  return (
    <Section title="Devil's advocacy">
      <div className="report-reader-callout">
        <p className="report-reader-callout-title">Challenge to {advocacy.target}</p>
        <p className="mt-1">
          {advocacy.argument}
          <Labels labels={advocacy.evidence} />
        </p>
        <p className="mt-2 text-[0.82rem] opacity-85">
          {lowered
            ? `Confidence on ${advocacy.target} lowered from ${advocacy.confidence_before ?? ''} to ${advocacy.confidence_after ?? ''}.`
            : 'Confidence unchanged.'}{' '}
          {advocacy.rationale}
        </p>
      </div>
    </Section>
  );
}

function KeyJudgement({
  judgement,
  index,
}: {
  judgement: ReportBody['key_judgements'][number];
  index: number;
}) {
  return (
    <li className="report-reader-judgement">
      <span className="report-reader-judgement-index">{String(index + 1).padStart(2, '0')}</span>
      <div className="min-w-0">
        <p className="report-reader-judgement-statement">
          {judgement.statement}
          <Labels labels={judgement.supporting_evidence} />
        </p>
        <div className="report-reader-facts">
          <span className="report-reader-fact">
            <span>Likelihood</span>
            <span>{probabilityTerm(judgement.probability)}</span>
          </span>
          <span className="report-reader-fact">
            <span>Confidence</span>
            <span>{judgement.confidence}</span>
          </span>
        </div>
        <p className="report-reader-note">{judgement.confidence_statement}</p>
        {judgement.contradicting_evidence.length > 0 && (
          <p className="report-reader-note">
            Contrary evidence: <Labels labels={judgement.contradicting_evidence} />
          </p>
        )}
        {judgement.indicators.length > 0 && (
          <p className="report-reader-note">Watch for: {judgement.indicators.join('; ')}</p>
        )}
      </div>
    </li>
  );
}

/** The body of a report, judgements first, every claim with its evidence labels. */
export function ReportBodyView({
  body,
}: {
  body: ReportBody;
  assessment?: ReportAssessment | null | undefined;
  citationChecks?: CitationChecks | null | undefined;
}) {
  return (
    <div>
      {body.key_judgements.length > 0 && (
        <Section title="Executive summary">
          <ol className="mt-3">
            {body.key_judgements.map((judgement, index) => (
              <KeyJudgement key={judgement.id} judgement={judgement} index={index} />
            ))}
          </ol>
        </Section>
      )}
      {body.reporting.length > 0 && (
        <Section title="Findings">
          {body.reporting.map((theme) => (
            <div key={theme.theme}>
              <h3 className="report-reader-subheading">{theme.theme}</h3>
              <ul className={BULLETS}>
                {theme.items.map((item, index) => (
                  <li key={index}>
                    {item.text}
                    <Labels labels={item.evidence} />
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </Section>
      )}
      {body.assessment.length > 0 && (
        <Section title="Analysis">
          {body.assessment.map((section) => (
            <div key={section.heading}>
              <h3 className="report-reader-subheading">{section.heading}</h3>
              <p className="report-reader-paragraph">
                {section.text}
                <Labels labels={section.evidence} />
              </p>
            </div>
          ))}
        </Section>
      )}
      {body.assumptions.length > 0 && (
        <Section title="Assumptions">
          <ul className={BULLETS}>
            {body.assumptions.map((assumption) => (
              <li key={assumption.id}>
                {assumption.text}
                {assumption.lynchpin && (
                  <span className="ml-1 text-xs font-semibold text-[color:var(--paper-accent)]">
                    (critical)
                  </span>
                )}
              </li>
            ))}
          </ul>
        </Section>
      )}
      {body.alternative_hypotheses.length > 0 && (
        <Section title="Alternative explanations">
          <ul className={BULLETS}>
            {body.alternative_hypotheses.map((alternative, index) => (
              <li key={index}>
                {alternative.text}
                <Labels labels={alternative.evidence} />
                <span className="text-[color:var(--paper-ink-soft)]">
                  {' '}
                  Why it is less likely: {alternative.why_less_likely}
                </span>
              </li>
            ))}
          </ul>
        </Section>
      )}
      <Section title="Indicators and warning">
        <p className="report-reader-paragraph">
          Current watch condition:{' '}
          <strong className="capitalize">{body.indicators_and_warning.watch_condition}</strong>
        </p>
        {body.indicators_and_warning.changes.length > 0 && (
          <ul className={BULLETS}>
            {body.indicators_and_warning.changes.map((change, index) => (
              <li key={index}>{change}</li>
            ))}
          </ul>
        )}
      </Section>
      {(body.gaps.length > 0 || body.collection_recommendations.length > 0) && (
        <Section title="Limitations and further research">
          <ul className={BULLETS}>
            {body.gaps.map((gap, index) => (
              <li key={`gap-${index}`}>{gap.text}</li>
            ))}
            {body.collection_recommendations.map((item, index) => (
              <li key={`rec-${index}`}>Recommend: {item}</li>
            ))}
          </ul>
        </Section>
      )}
      {body.sourcing_statement && (
        <Section title="Source note">
          <p className="report-reader-paragraph">{body.sourcing_statement}</p>
        </Section>
      )}
    </div>
  );
}

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
      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
        {rows.map(([id, text]) => (
          <div key={id} className="contents">
            <dt className="font-mono text-xs text-muted">{id}</dt>
            <dd>{text}</dd>
          </div>
        ))}
      </dl>
      {direction.search_terms.length > 0 && (
        <p className="text-xs text-muted">Search terms: {direction.search_terms.join(', ')}</p>
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
      <div className="rounded-card border border-amber-300/40 bg-surface p-3 text-sm">
        <p>
          <span className="mr-2 font-mono text-xs text-muted">on {advocacy.target}</span>
          {advocacy.argument}
          <Labels labels={advocacy.evidence} />
        </p>
        <p className="mt-1 text-xs text-muted">
          {lowered
            ? `Confidence on ${advocacy.target} lowered from ${advocacy.confidence_before ?? ''} to ${advocacy.confidence_after ?? ''}.`
            : 'Confidence unchanged.'}{' '}
          {advocacy.rationale}
        </p>
      </div>
    </Section>
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
    <div className="text-[0.94rem]">
      {body.key_judgements.length > 0 && (
        <Section title="Executive summary">
          <ol className="mt-4 space-y-5">
            {body.key_judgements.map((judgement, index) => (
              <li key={judgement.id} className="grid grid-cols-[1.75rem_minmax(0,1fr)] gap-3">
                <span className="pt-0.5 font-mono text-xs text-[#9b3b18]">
                  {String(index + 1).padStart(2, '0')}
                </span>
                <div>
                  <p className="font-semibold leading-7">
                    {judgement.statement}
                    <Labels labels={judgement.supporting_evidence} />
                  </p>
                  <p className="mt-1.5 text-xs leading-5 text-[#6d675e]">
                    <span className="font-semibold text-[#9b3b18]">
                      {probabilityTerm(judgement.probability)}
                    </span>
                    {' · '}
                    <span>{judgement.confidence} confidence</span> ·{' '}
                    {judgement.confidence_statement}
                  </p>
                  {judgement.contradicting_evidence.length > 0 && (
                    <p className="mt-1 text-xs leading-5 text-[#6d675e]">
                      Contrary evidence: <Labels labels={judgement.contradicting_evidence} />
                    </p>
                  )}
                  {judgement.indicators.length > 0 && (
                    <p className="mt-1 text-xs leading-5 text-[#6d675e]">
                      Watch for: {judgement.indicators.join('; ')}
                    </p>
                  )}
                </div>
              </li>
            ))}
          </ol>
        </Section>
      )}
      {body.reporting.length > 0 && (
        <Section title="Findings">
          {body.reporting.map((theme) => (
            <div key={theme.theme} className="mt-5">
              <h3 className="report-reader-subheading">{theme.theme}</h3>
              <ul className="mt-2 list-disc space-y-1.5 pl-5 marker:text-[#b9633e]">
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
            <div key={section.heading} className="mt-5">
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
          <ul className="mt-3 list-disc space-y-2 pl-5 marker:text-[#b9633e]">
            {body.assumptions.map((assumption) => (
              <li key={assumption.id}>
                {assumption.text}
                {assumption.lynchpin && (
                  <span className="ml-1 text-xs font-medium text-[#9b3b18]">(critical)</span>
                )}
              </li>
            ))}
          </ul>
        </Section>
      )}
      {body.alternative_hypotheses.length > 0 && (
        <Section title="Alternative explanations">
          <ul className="mt-3 list-disc space-y-2 pl-5 marker:text-[#b9633e]">
            {body.alternative_hypotheses.map((alternative, index) => (
              <li key={index}>
                {alternative.text}
                <Labels labels={alternative.evidence} />
                <span className="text-[#6d675e]">
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
          <ul className="mt-2 list-disc space-y-1 pl-5 marker:text-[#b9633e]">
            {body.indicators_and_warning.changes.map((change, index) => (
              <li key={index}>{change}</li>
            ))}
          </ul>
        )}
      </Section>
      {(body.gaps.length > 0 || body.collection_recommendations.length > 0) && (
        <Section title="Limitations and further research">
          <ul className="mt-3 list-disc space-y-2 pl-5 marker:text-[#b9633e]">
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

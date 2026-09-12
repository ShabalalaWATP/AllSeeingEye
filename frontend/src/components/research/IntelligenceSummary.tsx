import { useId, useState } from 'react';
import type { ReactNode } from 'react';
import { Link } from 'react-router';

import { SourceLink } from '@/components/ui/SourceLink';
import { SourceRatingDetails } from '@/components/sources/SourceRatingDetails';
import type { Report } from '@/lib/api/reports';
import { probabilityTerm } from '@/lib/doctrine';
import {
  intelligenceSummaryModel,
  sourceGradeDescription,
  type SummaryJudgement,
} from './intelligenceSummaryModel';

function JudgementContext({
  judgements,
  citations,
}: {
  judgements: SummaryJudgement[] | undefined;
  citations: (labels: readonly string[]) => ReactNode;
}) {
  if (!judgements?.length) return null;
  return (
    <div className="mt-3 max-w-[70ch] space-y-4">
      {judgements.map((judgement) => (
        <section key={judgement.id} aria-label={`Confidence and likelihood for ${judgement.id}`}>
          <dl className="flex flex-wrap gap-x-7 gap-y-2 text-xs leading-5">
            <div>
              <dt className="text-muted">Assessed likelihood</dt>
              <dd className="font-medium capitalize text-ember">
                {probabilityTerm(judgement.probability) || 'Not recorded'}
              </dd>
            </div>
            <div>
              <dt className="text-muted">Analytical confidence</dt>
              <dd className="font-medium capitalize">
                {judgement.assessment?.final_confidence ?? (judgement.confidence || 'Not recorded')}
              </dd>
            </div>
          </dl>
          <p className="mt-2 text-xs leading-6 text-muted">
            <span className="font-medium text-text">Confidence rationale: </span>
            {judgement.rationale || 'Not recorded for this judgement.'}
          </p>
          {judgement.supportingEvidence.length > 0 && (
            <p className="mt-1 text-xs leading-6 text-muted">
              Supporting evidence cited{citations(judgement.supportingEvidence)}
            </p>
          )}
          {judgement.contraryEvidence.length > 0 && (
            <p className="mt-1 text-xs leading-6 text-muted">
              Contrary evidence cited{citations(judgement.contraryEvidence)}
            </p>
          )}
          {judgement.assessment && (
            <details className="mt-2 text-xs leading-6 text-muted">
              <summary className="w-fit cursor-pointer text-ember">Evidence review</summary>
              <p className="mt-2">
                <span className="capitalize">{judgement.assessment.status}</span> judgement.
                Recorded confidence ceiling: {judgement.assessment.confidence_ceiling}.
              </p>
              <ul className="mt-2 list-disc space-y-1 pl-4">
                {judgement.assessment.explanation.map((text, index) => (
                  <li key={index}>{text}</li>
                ))}
              </ul>
            </details>
          )}
        </section>
      ))}
    </div>
  );
}

function AssessmentGuide() {
  return (
    <details className="max-w-[75ch] text-xs leading-6 text-muted">
      <summary className="w-fit cursor-pointer font-medium text-text">
        Understanding likelihood, confidence and source grades
      </summary>
      <div className="mt-3 space-y-3">
        <p>
          Likelihood describes how likely a judgement is to be true or occur. Analytical confidence
          describes the strength and stability of its basis. A highly likely judgement can still
          have low confidence.
        </p>
        <p>
          The app uses the UK probability yardstick and separate source reliability (A to F) and
          information credibility (1 to 6) grades. F and 6 mean there is not enough basis to judge,
          not that the information is false. Grades shown here were saved with this report.
        </p>
        <p>
          Repeated articles do not provide independent confirmation. Stronger evidence can outweigh
          several weak sources; grades are not calculated truth percentages. The app applies its own
          evidence policy informed by public doctrine, not an official NATO scoring algorithm.
        </p>
        <div className="flex flex-wrap gap-x-5 gap-y-2">
          <SourceLink url="https://www.gov.uk/government/publications/explaining-uncertainty-in-uk-intelligence-assessment/explaining-uncertainty-in-uk-intelligence-assessment">
            UK probability yardstick and confidence guidance
          </SourceLink>
          <SourceLink url="https://assets.publishing.service.gov.uk/media/653a4b0780884d0013f71bb0/JDP_2_00_Ed_4_web.pdf">
            UK MOD intelligence doctrine (JDP 2-00)
          </SourceLink>
        </div>
      </div>
    </details>
  );
}

/** Preserve the author's paragraphs rather than guessing sentence or claim boundaries. */
function AuthoredProse({
  text,
  citations,
  lead = false,
}: {
  text: string;
  citations: ReactNode;
  lead?: boolean;
}) {
  const paragraphs = text.split(/\r?\n\s*\r?\n/).filter((paragraph) => paragraph.trim());
  return (
    <div className="max-w-[70ch] space-y-3">
      {paragraphs.map((paragraph, index) => (
        <p
          key={index}
          className={`whitespace-pre-line ${lead && index === 0 ? 'text-base leading-7' : 'text-sm leading-7 text-text/90'}`}
        >
          {paragraph.trim()}
          {index === paragraphs.length - 1 && citations}
        </p>
      ))}
    </div>
  );
}

export function IntelligenceSummary({ report, subject }: { report: Report; subject: string }) {
  const [sourcesOpen, setSourcesOpen] = useState(false);
  const sourceId = useId();
  const summary = intelligenceSummaryModel(report);
  const citations = (labels: readonly string[]) =>
    [...new Set(labels)]
      .map((label) => summary.references.findIndex((item) => item.label === label) + 1)
      .filter((number) => number > 0)
      .map((number) => (
        <a
          key={number}
          href={`#${sourceId}-reference-${number}`}
          onClick={() => setSourcesOpen(true)}
          aria-label={`Daily briefing reference ${number}`}
          className="ml-1 align-super text-[10px] font-medium text-ember hover:underline focus-visible:outline-2 focus-visible:outline-ember"
        >
          [{number}]
        </a>
      ));
  return (
    <article aria-label={`${subject} briefing summary`} className="space-y-7">
      {report.version.status !== 'ready' && (
        <p className="border-l-2 border-amber pl-3 text-sm leading-6 text-amber">
          This briefing needs review. Check its evidence and limitations before relying on it.
        </p>
      )}
      {summary.missingReferences && (
        <p className="text-sm leading-6 text-amber">
          Some references could not be matched to the saved evidence. Check the full report.
        </p>
      )}
      <section aria-label="Executive summary" className="space-y-3">
        <h3 className="text-base font-semibold">Executive summary</h3>
        {summary.lead ? (
          <>
            <AuthoredProse
              text={summary.lead.text}
              citations={citations(summary.lead.evidence)}
              lead
            />
            <JudgementContext judgements={summary.lead.judgements} citations={citations} />
          </>
        ) : (
          <p className="text-sm leading-6 text-muted">
            There is not enough evidence for an overall {subject.toLowerCase()} assessment.
          </p>
        )}
      </section>
      {summary.keyPoints.length > 0 && (
        <section aria-label="Key points" className="space-y-3">
          <h3 className="text-base font-semibold">Key points</h3>
          <ul className="max-w-[70ch] list-disc space-y-4 pl-5 marker:text-ember">
            {summary.keyPoints.map((item, index) => (
              <li key={index} className="pl-1">
                <AuthoredProse text={item.text} citations={citations(item.evidence)} />
                <JudgementContext judgements={item.judgements} citations={citations} />
              </li>
            ))}
          </ul>
        </section>
      )}
      {summary.developments.length > 0 && (
        <section aria-label="Reported developments" className="space-y-5 border-t border-line pt-6">
          <h3 className="text-base font-semibold">Reported developments</h3>
          <div className="grid gap-x-10 gap-y-6 xl:grid-cols-2">
            {summary.developments.map((group, index) => (
              <section key={index} className="space-y-3">
                <h4 className="text-sm font-semibold text-ember">{group.theme}</h4>
                <ul className="space-y-3">
                  {group.items.map((item, itemIndex) => (
                    <li key={itemIndex}>
                      <AuthoredProse text={item.text} citations={citations(item.evidence)} />
                    </li>
                  ))}
                </ul>
              </section>
            ))}
          </div>
        </section>
      )}
      {summary.analysis.length > 0 && (
        <section aria-label="Detailed assessment" className="space-y-5 border-t border-line pt-6">
          <h3 className="text-base font-semibold">Analysis and implications</h3>
          <div className="divide-y divide-line/60">
            {summary.analysis.map((item, index) => (
              <section
                key={index}
                className="grid gap-3 py-5 first:pt-0 last:pb-0 lg:grid-cols-[minmax(10rem,0.35fr)_1fr] lg:gap-8"
              >
                <h4 className="text-sm font-semibold leading-7">{item.heading}</h4>
                <AuthoredProse text={item.text} citations={citations(item.evidence)} lead />
              </section>
            ))}
          </div>
        </section>
      )}
      {summary.watch.length > 0 && (
        <section aria-label="Developments to watch" className="space-y-3 border-t border-line pt-6">
          <h3 className="text-base font-semibold">Developments to watch</h3>
          <p className="max-w-[70ch] text-xs leading-5 text-muted">
            Conditions to monitor, not confirmed future events or forecasts.
          </p>
          <ul className="max-w-[70ch] list-disc space-y-2 pl-5 text-sm leading-7 marker:text-ember">
            {summary.watch.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>
      )}
      {summary.gaps.length > 0 && (
        <section
          aria-label="Coverage and limitations"
          className="space-y-3 border-t border-line pt-6"
        >
          <h3 className="text-sm font-semibold">Coverage and limitations</h3>
          <ul className="max-w-[70ch] space-y-2 text-sm leading-6 text-muted">
            {summary.gaps.map((gap, index) => (
              <li key={index}>{gap.text}</li>
            ))}
          </ul>
        </section>
      )}
      <footer className="space-y-4 border-t border-line pt-5">
        <AssessmentGuide />
        <Link
          to={`/reports/${report.report.id}`}
          className="text-sm font-medium text-ember hover:underline"
        >
          Read full briefing and export
        </Link>
        {summary.references.length > 0 && (
          <details
            open={sourcesOpen}
            onToggle={(event) => setSourcesOpen(event.currentTarget.open)}
          >
            <summary className="w-fit cursor-pointer text-xs text-muted hover:text-text">
              Sources cited in this summary ({summary.references.length})
            </summary>
            <ol className="mt-4 max-w-[80ch] space-y-3 text-xs leading-5 text-muted">
              {summary.references.map((item, index) => (
                <li key={item.label} id={`${sourceId}-reference-${index + 1}`}>
                  [{index + 1}] {item.source_name}: {item.title}.{' '}
                  <SourceLink url={item.url}>Open source</SourceLink>
                  <p className="mt-1 font-medium text-text">
                    Saved evidence grade: {item.grade || 'Not recorded'}
                  </p>
                  {item.grade && <p>{sourceGradeDescription(item.grade)}</p>}
                  <p>{item.grade_rationale || 'Grade rationale not recorded.'}</p>
                  <SourceRatingDetails rating={item.source_rating} frozen />
                </li>
              ))}
            </ol>
          </details>
        )}
      </footer>
    </article>
  );
}

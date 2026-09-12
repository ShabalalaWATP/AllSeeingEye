import { useId, useState } from 'react';
import { Link } from 'react-router';

import { SourceLink } from '@/components/ui/SourceLink';
import { SourceRatingDetails } from '@/components/sources/SourceRatingDetails';
import type { Report } from '@/lib/api/reports';
import { probabilityTerm } from '@/lib/doctrine';
import { sourceGradeDescription } from './intelligenceSummaryModel';

/** A compact cited preview, with the complete report and exports one click away. */
export function DailyBriefingSummary({
  report,
  detailed = false,
}: {
  report: Report;
  detailed?: boolean;
}) {
  const [sourcesOpen, setSourcesOpen] = useState(false);
  const sourceId = useId();
  const { body, evidence, status } = report.version;
  const summary = body.key_judgements.length
    ? body.key_judgements.slice(0, detailed ? 8 : 4).map((item) => ({
        text: item.statement,
        evidence: item.supporting_evidence,
        contrary: item.contradicting_evidence,
        judgement: item,
        confidence:
          report.version.assessment?.judgements.find((saved) => saved.judgement_id === item.id)
            ?.final_confidence ?? item.confidence,
      }))
    : body.assessment.slice(0, 3).map((item) => ({
        ...item,
        contrary: [],
        judgement: null,
        confidence: '',
      }));
  const news = body.reporting.flatMap((theme) => theme.items).slice(0, detailed ? 12 : 6);
  const analysis = detailed ? body.assessment.slice(0, 8) : [];
  const watch = detailed
    ? [...new Set(body.key_judgements.slice(0, 8).flatMap((item) => item.indicators))].slice(0, 8)
    : [];
  const usedLabels = new Set([
    ...summary.flatMap((item) => [...item.evidence, ...item.contrary]),
    ...[...news, ...analysis].flatMap((item) => item.evidence),
  ]);
  const references = evidence.filter((item) => usedLabels.has(item.label));
  const knownLabels = new Set(references.map((item) => item.label));
  const missingReferences = [...usedLabels].some((label) => !knownLabels.has(label));
  const citations = (labels: readonly string[]) => {
    const numbers = [
      ...new Set(labels.map((label) => references.findIndex((item) => item.label === label) + 1)),
    ].filter((number) => number > 0);
    return numbers.map((number) => (
      <a
        key={number}
        href={`#${sourceId}-briefing-reference-${number}`}
        className="ml-1 text-xs text-ember hover:underline"
        onClick={() => setSourcesOpen(true)}
        aria-label={`Daily briefing reference ${number}`}
      >
        [{number}]
      </a>
    ));
  };
  return (
    <article aria-label="Daily situation briefing" className="space-y-5">
      {status !== 'ready' && (
        <p className="border-l-2 border-amber pl-3 text-sm text-amber">
          This briefing needs review. Check its evidence and limitations before relying on it.
        </p>
      )}
      {missingReferences && (
        <p className="text-xs leading-5 text-amber">
          Some references could not be matched to the saved evidence. Check the full report.
        </p>
      )}
      <div className="grid gap-8 lg:grid-cols-[1.1fr_1fr]">
        <section aria-label="Overall situation">
          <h3 className="mb-3 text-base font-semibold">Overall situation</h3>
          {body.key_judgements.length > 0 && (
            <p className="mb-3 text-xs leading-5 text-muted">
              Likelihood uses the UK probability yardstick. Confidence describes the strength of the
              judgement's basis.
            </p>
          )}
          {summary.length ? (
            <ul className="space-y-3 text-sm leading-6">
              {summary.map((item, index) => (
                <li key={index}>
                  <p>
                    {item.text}
                    {!item.judgement && citations(item.evidence)}
                  </p>
                  {item.judgement && (
                    <section
                      aria-label={`Confidence and likelihood for ${item.judgement.id}`}
                      className="mt-2 space-y-1 text-xs leading-5"
                    >
                      <dl className="flex flex-wrap gap-x-5 gap-y-2">
                        <div>
                          <dt className="text-muted">Assessed likelihood</dt>
                          <dd className="font-medium capitalize text-ember">
                            {probabilityTerm(item.judgement.probability) || 'Not recorded'}
                          </dd>
                        </div>
                        <div>
                          <dt className="text-muted">Analytical confidence</dt>
                          <dd className="font-medium capitalize">
                            {item.confidence || 'Not recorded'}
                          </dd>
                        </div>
                      </dl>
                      <p className="pt-1 text-muted">
                        Confidence rationale:{' '}
                        {item.judgement.confidence_statement || 'Not recorded for this judgement.'}
                      </p>
                      {item.evidence.length > 0 && (
                        <p className="text-muted">Supporting evidence{citations(item.evidence)}</p>
                      )}
                      {item.contrary.length > 0 && (
                        <p className="text-muted">Contrary evidence{citations(item.contrary)}</p>
                      )}
                    </section>
                  )}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted">
              There is not enough evidence for an overall assessment.
            </p>
          )}
        </section>
        <section aria-label="Latest news">
          <h3 className="mb-3 text-base font-semibold">Latest news</h3>
          {news.length ? (
            <ul className="divide-y divide-line/60 text-sm leading-6">
              {news.map((item, index) => (
                <li key={index} className="py-2 first:pt-0">
                  {item.text}
                  {citations(item.evidence)}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted">No sourced news was available for this briefing.</p>
          )}
        </section>
      </div>
      {analysis.length > 0 && (
        <section aria-label="Detailed assessment" className="space-y-5 border-t border-line pt-5">
          <h3 className="text-base font-semibold">Analysis and implications</h3>
          <div className="grid gap-x-8 gap-y-6 lg:grid-cols-2">
            {analysis.map((item, index) => (
              <section key={index} className="space-y-2">
                <h4 className="text-sm font-semibold">{item.heading}</h4>
                <p className="text-sm leading-6">
                  {item.text}
                  {citations(item.evidence)}
                </p>
              </section>
            ))}
          </div>
        </section>
      )}
      {watch.length > 0 && (
        <section aria-label="Developments to watch" className="border-t border-line pt-5">
          <h3 className="text-base font-semibold">Developments to watch</h3>
          <p className="mt-2 text-xs text-muted">
            Conditions identified by the assessment to monitor, not confirmed future events.
          </p>
          <ul className="mt-3 grid list-disc gap-x-8 gap-y-2 pl-4 text-sm leading-6 lg:grid-cols-2">
            {watch.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>
      )}
      {body.gaps.length > 0 && (
        <p className="text-xs leading-5 text-muted">
          Coverage gaps:{' '}
          {body.gaps
            .slice(0, detailed ? 8 : 2)
            .map((gap) => gap.text)
            .join(' ')}
        </p>
      )}
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line pt-4">
        <Link
          to={`/reports/${report.report.id}`}
          className="text-sm font-medium text-ember hover:underline"
        >
          Read full briefing and export
        </Link>
        {references.length > 0 && (
          <details
            className="basis-full"
            open={sourcesOpen}
            onToggle={(event) => setSourcesOpen(event.currentTarget.open)}
          >
            <summary className="w-fit cursor-pointer text-xs text-muted hover:text-text">
              Sources cited in this summary ({references.length})
            </summary>
            <p className="mt-3 max-w-3xl text-xs leading-5 text-muted">
              Saved grades separate source reliability (A to F) from information credibility (1 to
              6). F and 6 mean there was not enough basis to judge, not that the information is
              false.
            </p>
            <ol className="mt-3 space-y-2 text-xs text-muted">
              {references.map((item, index) => (
                <li key={item.label} id={`${sourceId}-briefing-reference-${index + 1}`}>
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
      </div>
    </article>
  );
}

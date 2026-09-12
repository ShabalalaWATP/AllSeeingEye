import { useId, useState } from 'react';
import type { ReactNode } from 'react';
import { Link } from 'react-router';

import { SourceLink } from '@/components/ui/SourceLink';
import type { Report } from '@/lib/api/reports';
import { economySummaryModel } from './economySummaryModel';

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

export function EconomySummary({ report }: { report: Report }) {
  const [sourcesOpen, setSourcesOpen] = useState(false);
  const sourceId = useId();
  const summary = economySummaryModel(report);
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
    <article aria-label="Economic briefing summary" className="space-y-7">
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
          <AuthoredProse
            text={summary.lead.text}
            citations={citations(summary.lead.evidence)}
            lead
          />
        ) : (
          <p className="text-sm leading-6 text-muted">
            There is not enough evidence for an overall economic assessment.
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
                </li>
              ))}
            </ol>
          </details>
        )}
      </footer>
    </article>
  );
}

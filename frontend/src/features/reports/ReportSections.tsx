import type { ReactNode } from 'react';

import type {
  DevilsAdvocacy,
  Direction,
  EvidenceItem,
  Finding,
  ReportBody,
} from '@/lib/api/reports';
import { probabilityTerm } from '@/lib/doctrine';
import { formatUtc } from '@/lib/format';
import { isHttpUrl } from '@/lib/urls';

function Labels({ labels }: { labels: readonly string[] }) {
  if (labels.length === 0) return null;
  return (
    <span className="ml-1 inline-flex flex-wrap gap-1 align-middle">
      {labels.map((label) => (
        <span key={label} className="rounded bg-surface-2 px-1 font-mono text-[10px] text-muted">
          {label}
        </span>
      ))}
    </span>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section aria-label={title} className="flex flex-col gap-2">
      <h2 className="text-base font-semibold text-text">{title}</h2>
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
export function ReportBodyView({ body }: { body: ReportBody }) {
  return (
    <div className="flex flex-col gap-6 text-sm text-text">
      {body.key_judgements.length > 0 && (
        <Section title="Key judgements">
          <ol className="flex flex-col gap-3">
            {body.key_judgements.map((judgement) => (
              <li key={judgement.id} className="rounded-card border border-line bg-surface p-3">
                <p className="font-medium">
                  <span className="mr-2 font-mono text-xs text-muted">{judgement.id}</span>
                  {judgement.statement}
                  <Labels labels={judgement.supporting_evidence} />
                </p>
                <p className="mt-1 text-xs text-muted">
                  <span className="rounded bg-ember/15 px-1.5 py-0.5 font-mono text-ember">
                    {probabilityTerm(judgement.probability)}
                  </span>{' '}
                  <span className="rounded bg-surface-2 px-1.5 py-0.5 font-mono">
                    {judgement.confidence} confidence
                  </span>{' '}
                  {judgement.confidence_statement}
                </p>
                {judgement.contradicting_evidence.length > 0 && (
                  <p className="mt-1 text-xs text-muted">
                    Contradicting: <Labels labels={judgement.contradicting_evidence} />
                  </p>
                )}
                {judgement.indicators.length > 0 && (
                  <p className="mt-1 text-xs text-muted">
                    Indicators: {judgement.indicators.join('; ')}
                  </p>
                )}
              </li>
            ))}
          </ol>
        </Section>
      )}
      {body.reporting.length > 0 && (
        <Section title="Reporting">
          {body.reporting.map((theme) => (
            <div key={theme.theme}>
              <h3 className="text-sm font-semibold text-muted">{theme.theme}</h3>
              <ul className="list-disc pl-5">
                {theme.items.map((item, index) => (
                  <li key={index}>
                    {item.text}
                    <Labels labels={item.evidence} />
                    {item.grade && (
                      <span className="ml-1 font-mono text-[10px] text-muted">{item.grade}</span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </Section>
      )}
      {body.assessment.length > 0 && (
        <Section title="Assessment">
          {body.assessment.map((section) => (
            <div key={section.heading}>
              <h3 className="text-sm font-semibold text-muted">{section.heading}</h3>
              <p>
                {section.text}
                <Labels labels={section.evidence} />
              </p>
            </div>
          ))}
        </Section>
      )}
      {body.assumptions.length > 0 && (
        <Section title="Assumptions">
          <ul className="list-disc pl-5">
            {body.assumptions.map((assumption) => (
              <li key={assumption.id}>
                <span className="mr-1 font-mono text-xs text-muted">{assumption.id}</span>
                {assumption.text}
                {assumption.lynchpin && <span className="ml-1 text-xs text-ember">(lynchpin)</span>}
              </li>
            ))}
          </ul>
        </Section>
      )}
      {body.alternative_hypotheses.length > 0 && (
        <Section title="Alternative hypotheses">
          <ul className="list-disc pl-5">
            {body.alternative_hypotheses.map((alternative, index) => (
              <li key={index}>
                {alternative.text}
                <Labels labels={alternative.evidence} />
                <span className="text-muted"> Why less likely: {alternative.why_less_likely}</span>
              </li>
            ))}
          </ul>
        </Section>
      )}
      <Section title="Indicators and warning">
        <p>
          Watch condition:{' '}
          <span className="font-mono uppercase">{body.indicators_and_warning.watch_condition}</span>
        </p>
        {body.indicators_and_warning.changes.length > 0 && (
          <ul className="list-disc pl-5">
            {body.indicators_and_warning.changes.map((change, index) => (
              <li key={index}>{change}</li>
            ))}
          </ul>
        )}
      </Section>
      {(body.gaps.length > 0 || body.collection_recommendations.length > 0) && (
        <Section title="Gaps and collection">
          <ul className="list-disc pl-5">
            {body.gaps.map((gap, index) => (
              <li key={`gap-${index}`}>
                {gap.eei && <span className="mr-1 font-mono text-xs text-muted">{gap.eei}</span>}
                {gap.text}
              </li>
            ))}
            {body.collection_recommendations.map((item, index) => (
              <li key={`rec-${index}`}>Recommend: {item}</li>
            ))}
          </ul>
        </Section>
      )}
      <Section title="Sourcing statement">
        <p>{body.sourcing_statement || 'Not provided.'}</p>
      </Section>
    </div>
  );
}

export function EvidenceAnnex({
  evidence,
  findings,
  status,
}: {
  evidence: readonly EvidenceItem[];
  findings: readonly Finding[];
  status: string;
}) {
  const warnings = findings.filter((finding) => finding.severity === 'warning');
  return (
    <div className="flex flex-col gap-4 text-sm">
      {status === 'ready' && warnings.length > 0 && (
        <details className="text-xs text-muted">
          <summary>{warnings.length} validator note(s)</summary>
          <ul className="list-disc pl-5">
            {warnings.map((finding, index) => (
              <li key={index}>
                {finding.location}: {finding.message}
              </li>
            ))}
          </ul>
        </details>
      )}
      <Section title="Evidence annex">
        <div className="overflow-x-auto rounded-card border border-line bg-surface">
          <table className="w-full text-left text-xs">
            <caption className="sr-only">Evidence annex</caption>
            <thead>
              <tr className="text-muted">
                <th className="px-2 py-1">Label</th>
                <th className="px-2 py-1">Grade</th>
                <th className="px-2 py-1">Source</th>
                <th className="px-2 py-1">Published</th>
                <th className="px-2 py-1">Item</th>
                <th className="px-2 py-1">Archive</th>
              </tr>
            </thead>
            <tbody>
              {evidence.map((item) => (
                <tr key={item.label} className="border-t border-line/60 align-top">
                  <td className="px-2 py-1 font-mono">{item.label}</td>
                  <td className="px-2 py-1 font-mono" title={item.grade_rationale}>
                    {item.grade}
                  </td>
                  <td className="px-2 py-1">
                    {item.source_name}
                    {item.flags.length > 0 && (
                      <span className="ml-1 font-mono text-[10px] text-amber-300">
                        {item.flags.join(', ').replace(/_/g, ' ')}
                      </span>
                    )}
                  </td>
                  <td className="px-2 py-1 whitespace-nowrap">{formatUtc(item.published_at)}</td>
                  <td className="px-2 py-1">
                    {isHttpUrl(item.url) ? (
                      <a
                        href={item.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-ember hover:underline"
                      >
                        {item.title}
                      </a>
                    ) : (
                      item.title
                    )}
                  </td>
                  <td className="px-2 py-1">
                    {isHttpUrl(item.archive_url) ? (
                      <a
                        href={item.archive_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-muted hover:underline"
                      >
                        archive
                      </a>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>
    </div>
  );
}

import type { CitationChecks } from '@/lib/api/reportResearch';
import { Labels } from './EvidenceLinks';

const statusLabel = {
  absent: 'Excerpt absent',
  context_insufficient: 'Context insufficient',
  excerpt_present: 'Excerpt present',
  review_required: 'Review required',
} as const;

export function JudgementCitationChecks({
  check,
}: {
  check: CitationChecks['judgements'][number] | undefined;
}) {
  if (!check) return null;
  return (
    <details className="mt-3 min-w-0 border-t border-line pt-2 text-xs">
      <summary className="cursor-pointer py-2 font-medium focus-visible:outline-2 focus-visible:outline-ember">
        Citation excerpts · {statusLabel[check.status]}
      </summary>
      <div className="space-y-3 text-muted [overflow-wrap:anywhere]">
        <p>
          Literal checks against frozen original titles and snippets. Excerpt presence does not
          establish that a source supports the judgement or that the claim is true. Review
          indicators are not contradiction findings.
        </p>
        {check.reasons.map((reason, index) => (
          <p key={index}>{reason}</p>
        ))}
        {check.citations.length === 0 && <p>No citation checks recorded for this judgement.</p>}
        {check.citations.map((citation, index) => (
          <section
            key={index}
            aria-label={`${citation.label} ${citation.relation} citation check`}
            className="space-y-2 border-l-2 border-line pl-3"
          >
            <p className="text-text">
              <Labels labels={[citation.label]} /> · Model-assigned {citation.relation} ·{' '}
              {statusLabel[citation.status]}
            </p>
            {citation.excerpt && (
              <>
                <blockquote className="whitespace-pre-wrap border-l-2 border-ember/40 pl-3 text-text">
                  {citation.excerpt.text}
                </blockquote>
                <details>
                  <summary className="cursor-pointer py-2">Exact excerpt provenance</summary>
                  <dl className="space-y-2 font-mono text-[11px]">
                    <div>
                      <dt>Original field / offsets</dt>
                      <dd>
                        {citation.excerpt.field} / {citation.excerpt.start} to{' '}
                        {citation.excerpt.end}
                      </dd>
                    </div>
                    <div>
                      <dt>Excerpt SHA-256</dt>
                      <dd>{citation.excerpt.sha256}</dd>
                    </div>
                    <div>
                      <dt>Source content hash</dt>
                      <dd>{citation.source_content_hash ?? 'Not recorded'}</dd>
                    </div>
                    <div>
                      <dt>Evidence ID</dt>
                      <dd>{citation.evidence_id ?? 'Not recorded'}</dd>
                    </div>
                  </dl>
                </details>
              </>
            )}
            {citation.reasons.map((reason, reasonIndex) => (
              <p key={reasonIndex}>{reason}</p>
            ))}
            {citation.indicators.map((indicator, indicatorIndex) => (
              <div key={indicatorIndex} className="space-y-1">
                <p className="font-medium text-amber">
                  Review cue: {indicator.kind.replace(/_/g, ' ')}
                </p>
                <p>{indicator.explanation}</p>
                <p>Claim values: {indicator.claim_values.join(', ') || 'None detected'}</p>
                <p>Excerpt values: {indicator.excerpt_values.join(', ') || 'None detected'}</p>
              </div>
            ))}
          </section>
        ))}
      </div>
    </details>
  );
}

export function CitationCheckMethod({ checks }: { checks: CitationChecks | null | undefined }) {
  if (!checks)
    return (
      <p className="text-xs text-muted">
        Citation checks not recorded for this version. No checks have been recomputed.
      </p>
    );
  return (
    <details className="text-xs text-muted">
      <summary className="cursor-pointer py-2 font-medium">
        Citation check method and limits
      </summary>
      <p className="mt-2 font-mono">Saved method: {checks.method_version}</p>
      {checks.judgements.length === 0 && (
        <p className="mt-2">No judgement citation checks recorded.</p>
      )}
      <ul className="mt-2 list-disc space-y-1 pl-4">
        {checks.limitations.map((text, index) => (
          <li key={index}>{text}</li>
        ))}
      </ul>
    </details>
  );
}

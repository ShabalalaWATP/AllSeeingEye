import type { ClaimLedger } from '@/lib/api/claimLedger';

const dimensionNames = {
  evidence_support: 'Evidence support',
  source_independence: 'Source independence',
  coverage: 'Research coverage',
  citation_validity: 'Citation validity',
};
const readable = (value: string) => value.replaceAll('_', ' ');

/** Every value comes from the authorised frozen report. No scoring takes place in the UI. */
export function ClaimLedgerView({ ledger }: { ledger: ClaimLedger | null | undefined }) {
  return (
    <section aria-labelledby="claim-ledger-title" className="space-y-4 border-t border-line pt-6">
      <header>
        <h2 id="claim-ledger-title" className="text-lg font-semibold">
          Claim inspection
        </h2>
        <p className="mt-2 text-sm text-muted">
          Inspect each saved judgement, its assigned evidence and uncertainty. These are analytical
          inferences, not verified facts or newly extracted atomic claims.
        </p>
      </header>
      {!ledger ? (
        <p className="text-sm text-muted">Claim inspection is unavailable for this response.</p>
      ) : (
        <>
          <p className="font-mono text-xs text-muted">
            Frozen report version {ledger.report_version}
          </p>
          {ledger.claims.length === 0 && (
            <p className="text-sm text-muted">No judgements were saved in this version.</p>
          )}
          {ledger.claims.map((claim) => (
            <details key={claim.id} className="rounded border border-line p-4">
              <summary className="cursor-pointer text-sm font-medium focus-visible:outline-2 focus-visible:outline-ember">
                {claim.judgement_id} · {claim.statement}
              </summary>
              <div className="mt-4 space-y-5 text-sm [overflow-wrap:anywhere]">
                <p className="font-mono text-xs text-muted">Analytical inference · ID {claim.id}</p>
                <dl className="grid gap-4 sm:grid-cols-2">
                  {claim.dimensions.map((dimension) => (
                    <div key={dimension.name}>
                      <dt className="font-medium">{dimensionNames[dimension.name]}</dt>
                      <dd className="mt-1 capitalize">{readable(dimension.status)}</dd>
                      <dd className="mt-1 text-xs text-muted">{dimension.explanation}</dd>
                    </div>
                  ))}
                </dl>
                <section aria-label={`${claim.judgement_id} uncertainty`} className="space-y-2">
                  <h3 className="font-medium">Uncertainty and assumptions</h3>
                  <p>{claim.confidence_statement || 'No confidence explanation recorded.'}</p>
                  {claim.assessment && (
                    <p className="text-xs text-muted">
                      Saved confidence: {claim.assessment.final_confidence} · Evidence ceiling:{' '}
                      {claim.assessment.confidence_ceiling}
                    </p>
                  )}
                  <p className="text-muted">
                    Assumption references: {claim.assumptions.join(', ') || 'None recorded'}
                  </p>
                  {claim.assessment?.limitations.map((text, i) => (
                    <p key={i} className="text-xs text-muted">
                      {text}
                    </p>
                  ))}
                </section>
                <section
                  aria-label={`${claim.judgement_id} evidence relationships`}
                  className="space-y-3"
                >
                  <h3 className="font-medium">Model-assigned support and opposition</h3>
                  {claim.sources.length === 0 && (
                    <p className="text-muted">No evidence relationships recorded.</p>
                  )}
                  {claim.sources.map((source) => (
                    <div
                      key={`${source.relation}:${source.label}`}
                      className="border-l-2 border-line pl-3"
                    >
                      <p>
                        <span className="font-mono">{source.label}</span> ·{' '}
                        {readable(source.relation)} ·{' '}
                        {source.source_name ?? 'Frozen evidence missing'}
                      </p>
                      <p className="text-xs text-muted">
                        Declared organisation: {source.organisation ?? 'Unknown'}
                      </p>
                      <p className="text-xs text-muted">
                        Evidence ID: {source.evidence_id ?? 'Unknown'} · Content hash:{' '}
                        {source.content_hash ?? 'Unknown'}
                      </p>
                      {claim.citation_checks?.citations
                        .filter(
                          (citation) =>
                            citation.label === source.label &&
                            citation.relation === source.relation,
                        )
                        .map((citation, i) => (
                          <div key={i} className="mt-2 space-y-2">
                            <p className="text-xs">Literal check: {readable(citation.status)}</p>
                            {citation.excerpt ? (
                              <>
                                <blockquote className="whitespace-pre-wrap border-l-2 border-ember/40 pl-3">
                                  {citation.excerpt.text}
                                </blockquote>
                                <p className="font-mono text-xs text-muted">
                                  {citation.excerpt.field} · offsets {citation.excerpt.start}–
                                  {citation.excerpt.end} · SHA-256 {citation.excerpt.sha256}
                                </p>
                              </>
                            ) : (
                              <p className="text-xs text-muted">No exact excerpt saved.</p>
                            )}
                            {citation.reasons.map((reason, index) => (
                              <p key={index} className="text-xs text-muted">
                                {reason}
                              </p>
                            ))}
                            {citation.indicators.map((indicator, index) => (
                              <p key={index} className="text-xs text-muted">
                                Review indicator: {readable(indicator.kind)} ·{' '}
                                {indicator.explanation}
                              </p>
                            ))}
                          </div>
                        ))}
                    </div>
                  ))}
                </section>
                {claim.assessment && (
                  <section className="space-y-2" aria-label={`${claim.judgement_id} source groups`}>
                    <h3 className="font-medium">Saved source groups</h3>
                    <p className="text-xs text-muted">
                      Declared organisation and possible-copy groups do not establish
                      original-source chains or independent reporting.
                    </p>
                    {(['support_groups', 'opposition_groups'] as const).map((relation) =>
                      claim.assessment?.[relation].map((group) => (
                        <p key={`${relation}:${group.id}`} className="text-xs">
                          {relation === 'support_groups' ? 'Supporting' : 'Opposing'} · {group.id}:{' '}
                          {group.labels.join(', ')} · {group.contribution} contribution
                          {group.possible_copy ? ' · Possible copies' : ''}
                          {!group.known_organisation ? ' · Organisation unknown' : ''}
                        </p>
                      )),
                    )}
                  </section>
                )}
              </div>
            </details>
          ))}
          <details className="text-sm text-muted">
            <summary className="cursor-pointer py-2">
              Report-level gaps and inspection limits
            </summary>
            <ul className="list-disc space-y-2 pl-5">
              {ledger.recorded_gaps.map((gap, index) => (
                <li key={index}>{gap}</li>
              ))}
            </ul>
            {ledger.recorded_gaps.length === 0 && (
              <p>No gaps recorded; coverage remains unknown.</p>
            )}
            <ul className="mt-3 list-disc space-y-2 pl-5">
              {ledger.limitations.map((limit, index) => (
                <li key={index}>{limit}</li>
              ))}
            </ul>
          </details>
        </>
      )}
    </section>
  );
}

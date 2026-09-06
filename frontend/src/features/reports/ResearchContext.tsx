import type { ResearchContext } from '@/lib/api/researchContext';
import { formatUtc } from '@/lib/format';
import { SourceLink } from '@/components/ui/SourceLink';
import { Labels } from './EvidenceLinks';

export function ResearchContextView({ context }: { context: ResearchContext | null | undefined }) {
  if (!context)
    return (
      <p className="text-xs text-muted">
        Timeline and source context not recorded for this version.
      </p>
    );
  return (
    <details className="min-w-0 border-t border-line py-3 text-sm">
      <summary className="cursor-pointer py-2 font-medium">Timeline and source context</summary>
      <div className="mt-3 space-y-6 [overflow-wrap:anywhere]">
        <p className="text-xs text-muted">
          Saved metadata, not verified identities or independent corroboration. Publication,
          observation and capture times describe different things. Candidates remain separate;
          declared links do not establish ownership or control.
        </p>
        <section aria-label="Publication timeline" className="space-y-3">
          <h2 className="font-semibold">Publication timeline</h2>
          {context.timeline.length === 0 && (
            <p className="text-xs text-muted">No timeline entries recorded.</p>
          )}
          <ol className="divide-y divide-line">
            {context.timeline.map((entry, index) => (
              <li key={index} className="space-y-2 py-3">
                <p>
                  <Labels labels={[entry.evidence_label]} /> {entry.title}
                </p>
                <dl className="grid gap-2 text-xs sm:grid-cols-3">
                  <div>
                    <dt className="text-muted">Published</dt>
                    <dd>{formatUtc(entry.published_at)}</dd>
                  </div>
                  <div>
                    <dt className="text-muted">Observed</dt>
                    <dd>{entry.observed_at ? formatUtc(entry.observed_at) : 'Not recorded'}</dd>
                  </div>
                  <div>
                    <dt className="text-muted">Captured</dt>
                    <dd>{formatUtc(entry.captured_at)}</dd>
                  </div>
                  <div>
                    <dt className="text-muted">Timestamp basis</dt>
                    <dd>{entry.timestamp_basis ?? 'Not recorded'}</dd>
                  </div>
                  <div>
                    <dt className="text-muted">Date precision</dt>
                    <dd>{entry.date_precision ?? 'Not recorded'}</dd>
                  </div>
                  <div>
                    <dt className="text-muted">Current snapshot</dt>
                    <dd>
                      {entry.current_snapshot === null
                        ? 'Not recorded'
                        : entry.current_snapshot
                          ? 'Yes'
                          : 'No'}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-muted">Record kind</dt>
                    <dd>{entry.record_kind ?? 'Not recorded'}</dd>
                  </div>
                  {entry.temporal_attributes.map((attribute, attributeIndex) => (
                    <div key={attributeIndex}>
                      <dt className="font-mono text-muted">{attribute.key}</dt>
                      <dd>
                        {attribute.value === null ? 'Not recorded (null)' : String(attribute.value)}
                      </dd>
                    </div>
                  ))}
                </dl>
                <ul className="list-disc space-y-1 pl-4 text-xs text-muted">
                  {entry.limitations.map((text, limitIndex) => (
                    <li key={limitIndex}>{text}</li>
                  ))}
                </ul>
              </li>
            ))}
          </ol>
        </section>
        <section aria-label="Identity candidates" className="space-y-3">
          <h2 className="font-semibold">Identity candidates</h2>
          <p className="text-xs text-muted">
            Unverified candidates, not resolved or merged identities.
          </p>
          {context.identity_candidates.length === 0 && (
            <p className="text-xs text-muted">No identity candidates recorded.</p>
          )}
          {context.identity_candidates.map((candidate, index) => (
            <div key={index} className="space-y-2 border-l border-line pl-3 text-xs">
              <p>
                <Labels labels={[candidate.evidence_label]} /> Declared match status:{' '}
                {candidate.declared_match_status ?? 'Not recorded'}
              </p>
              <dl className="space-y-2">
                {candidate.identifiers.map((identifier, row) => (
                  <div key={`id-${row}`}>
                    <dt className="text-muted">Identifier · {identifier.namespace}</dt>
                    <dd>{identifier.value}</dd>
                  </div>
                ))}
                {candidate.aliases.map((alias, row) => (
                  <div key={`alias-${row}`}>
                    <dt className="text-muted">Alias · {alias.namespace}</dt>
                    <dd>{alias.value}</dd>
                  </div>
                ))}
              </dl>
            </div>
          ))}
        </section>
        <section aria-label="Declared source links" className="space-y-3">
          <h2 className="font-semibold">Declared source links</h2>
          {context.source_chains.length === 0 && (
            <p className="text-xs text-muted">No source links recorded.</p>
          )}
          {context.source_chains.map((edge, index) => (
            <div key={index} className="space-y-1 border-l border-line pl-3 text-xs">
              <p>
                <Labels labels={[edge.evidence_label]} /> {edge.relation.replace(/_/g, ' ')} ·
                Unverified attribution
              </p>
              <p>
                {edge.declared_name ?? 'Name not recorded'} ·{' '}
                {edge.declared_id ?? 'ID not recorded'}
              </p>
              <p className="text-muted">Collector: {edge.collector_source_id}</p>
              <SourceLink url={edge.declared_url}>Open declared source link</SourceLink>
            </div>
          ))}
        </section>
        <section aria-label="Possible source relationships" className="space-y-3">
          <h2 className="font-semibold">Possible source relationships</h2>
          {context.source_relationships.length === 0 && (
            <p className="text-xs text-muted">No relationship hints recorded.</p>
          )}
          {context.source_relationships.map((relationship, index) => (
            <div key={index} className="space-y-1 text-xs">
              <p>
                <Labels labels={relationship.evidence_labels} /> Unverified relationship
              </p>
              {relationship.shared_parent && (
                <p>Declared shared parent: {relationship.shared_parent}</p>
              )}
              <ul className="list-disc pl-4 text-muted">
                {relationship.reasons.map((text, row) => (
                  <li key={row}>{text}</li>
                ))}
              </ul>
            </div>
          ))}
        </section>
        <p className="font-mono text-xs text-muted">
          Saved context method: {context.method_version}
        </p>
        <ul className="list-disc space-y-1 pl-4 text-xs text-muted">
          {context.limitations.map((text, index) => (
            <li key={index}>{text}</li>
          ))}
        </ul>
      </div>
    </details>
  );
}

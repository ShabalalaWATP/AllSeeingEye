import { useCallback, useState } from 'react';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { fetchIdentity } from '@/lib/api/identities';
import type { IdentityCandidate, IdentityRevision } from '@/lib/api/identities';
import type { EvidenceItem } from '@/lib/api/reports';
import { describeError } from '@/lib/api/errors';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { formatUtc } from '@/lib/format';
import { IdentityExportChoice } from './ClaimExportSelection';
import { Labels } from './EvidenceLinks';

export function CandidateFacts({
  candidate,
  attributes,
}: {
  candidate: IdentityCandidate;
  attributes: EvidenceItem['attributes'];
}) {
  return (
    <div className="space-y-2 text-xs [overflow-wrap:anywhere]">
      <p>
        Captured candidate {candidate.evidence_label} · Source match status:{' '}
        {candidate.declared_match_status ?? 'Not recorded'}
      </p>
      <dl className="space-y-2">
        {[...candidate.identifiers, ...candidate.aliases].map((item, index) => (
          <div key={index}>
            <dt className="text-muted">{item.namespace}</dt>
            <dd>{item.value}</dd>
          </div>
        ))}
      </dl>
      <details>
        <summary className="cursor-pointer py-2">Original captured attributes</summary>
        <dl className="space-y-2">
          {attributes?.map((item, index) => (
            <div key={index}>
              <dt className="font-mono text-muted">{item.key}</dt>
              <dd>{item.value === null ? 'Not recorded (null)' : String(item.value)}</dd>
            </div>
          ))}
        </dl>
      </details>
    </div>
  );
}

export function IdentityRevisionText({ value }: { value: IdentityRevision }) {
  return (
    <div className="space-y-3 text-sm [overflow-wrap:anywhere]">
      <p className="font-semibold">
        {value.disposition} · Candidate {value.candidate.candidate.evidence_label}
      </p>
      <p>Research subject: {value.subject}</p>
      <p className="text-xs text-muted">
        Revision {value.number} · {formatUtc(value.created_at)} · Author {value.authored_by}
      </p>
      <p>{value.rationale}</p>
      <CandidateFacts
        candidate={value.candidate.candidate}
        attributes={value.candidate.attributes}
      />
      {value.unresolved_conflicts.length > 0 && (
        <div>
          <h4 className="font-medium">Unresolved conflicts</h4>
          <ul className="list-disc pl-5">
            {value.unresolved_conflicts.map((text, i) => (
              <li key={i}>{text}</li>
            ))}
          </ul>
        </div>
      )}
      {value.citations.map((row, index) => (
        <blockquote key={index} className="border-l border-line pl-3">
          <p className="text-xs text-muted">
            <Labels labels={[row.label]} /> · {row.relation} · Original {row.excerpt.field}
          </p>
          <p>{row.excerpt.text}</p>
        </blockquote>
      ))}
    </div>
  );
}

export function IdentityHistory({ current }: { current: IdentityRevision }) {
  const [id, setId] = useState(current.id);
  const request = useScopedRequest();
  const loader = useCallback(
    () => fetchIdentity(current.decision_id, id, request()),
    [current.decision_id, id, request],
  );
  const resource = useScopedResource(loader);
  return (
    <div className="mt-4 space-y-3">
      {resource.loading && <LoadingNote label="Loading identity revision" />}
      {resource.error && <Alert tone="error">{describeError(resource.error)}</Alert>}
      {resource.data && (
        <>
          <IdentityRevisionText value={resource.data.revision} />
          <IdentityExportChoice value={resource.data.revision} />
          {resource.data.revision.previous_id && (
            <Button
              variant="secondary"
              onClick={() => {
                const previous = resource.data?.revision.previous_id;
                if (previous) setId(previous);
              }}
            >
              Previous identity revision
            </Button>
          )}
          {id !== current.id && (
            <Button variant="secondary" onClick={() => setId(current.id)}>
              Latest identity revision
            </Button>
          )}
        </>
      )}
    </div>
  );
}

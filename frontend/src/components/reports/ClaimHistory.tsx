import { useCallback, useState } from 'react';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { fetchClaim } from '@/lib/api/claims';
import type { ClaimRevision } from '@/lib/api/claims';
import { describeError } from '@/lib/api/errors';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { formatUtc } from '@/lib/format';
import { ClaimExportChoice } from './ClaimExportSelection';
import { Labels } from './EvidenceLinks';

export function RevisionText({ value }: { value: ClaimRevision }) {
  return (
    <div className="space-y-3 text-sm [overflow-wrap:anywhere]">
      <p className="font-medium">{value.statement}</p>
      <p className="text-xs text-muted">
        {value.state} · Revision {value.number} · {formatUtc(value.created_at)}
      </p>
      <p>{value.kind === 'reported_fact' ? 'Attributed reporting' : 'Analytical inference'}</p>
      {value.citations.map((citation, index) => (
        <blockquote key={index} className="border-l-2 border-line pl-3">
          <p className="text-xs text-muted">
            <Labels labels={[citation.label]} /> · {citation.relation} · Original{' '}
            {citation.excerpt.field}
          </p>
          <p>{citation.excerpt.text}</p>
        </blockquote>
      ))}
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
      {value.model_origin && (
        <details className="text-xs text-muted">
          <summary className="cursor-pointer">Model proposal provenance</summary>
          <dl className="mt-2 space-y-1">
            <div>
              <dt>Provider and returned model</dt>
              <dd>
                {value.model_origin.provider} · {value.model_origin.returned_model}
              </dd>
            </div>
            <div>
              <dt>Requested model</dt>
              <dd>{value.model_origin.requested_model}</dd>
            </div>
            <div>
              <dt>Generated</dt>
              <dd>{formatUtc(value.model_origin.generated_at)}</dd>
            </div>
            <div>
              <dt>Profile revision</dt>
              <dd>{value.model_origin.profile_revision}</dd>
            </div>
            <div>
              <dt>Method</dt>
              <dd>{value.model_origin.method_version}</dd>
            </div>
            <div>
              <dt>Input SHA-256</dt>
              <dd>{value.model_origin.input_sha256}</dd>
            </div>
          </dl>
        </details>
      )}
      <p className="text-muted">Revision reason: {value.reason}</p>
    </div>
  );
}

export function ClaimHistory({ current }: { current: ClaimRevision }) {
  const [revisionId, setRevisionId] = useState(current.id);
  const request = useScopedRequest();
  const loader = useCallback(
    () => fetchClaim(current.claim_id, revisionId, request()),
    [current.claim_id, revisionId, request],
  );
  const resource = useScopedResource(loader);
  return (
    <div className="mt-4 space-y-3">
      {resource.loading && <LoadingNote label="Loading claim revision" />}
      {resource.error && <Alert tone="error">{describeError(resource.error)}</Alert>}
      {resource.data && (
        <>
          <RevisionText value={resource.data.revision} />
          <ClaimExportChoice value={resource.data.revision} />
          <div className="flex flex-wrap gap-2">
            {resource.data.revision.previous_id && (
              <Button
                variant="secondary"
                onClick={() => {
                  const previous = resource.data?.revision.previous_id;
                  if (previous) setRevisionId(previous);
                }}
              >
                Previous revision
              </Button>
            )}
            {revisionId !== current.id && (
              <Button variant="secondary" onClick={() => setRevisionId(current.id)}>
                Latest revision
              </Button>
            )}
          </div>
        </>
      )}
    </div>
  );
}

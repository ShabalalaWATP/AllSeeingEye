import { useCallback, useState } from 'react';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { fetchRelationship } from '@/lib/api/relationships';
import type { RelationshipRevision } from '@/lib/api/relationships';
import { describeError } from '@/lib/api/errors';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { formatUtc } from '@/lib/format';
import { RelationshipExportChoice } from './ClaimExportSelection';
import { Labels } from './EvidenceLinks';
import { RelationshipFacts } from './RelationshipFacts';

export function RelationshipRevisionText({ value }: { value: RelationshipRevision }) {
  return (
    <div className="space-y-3 text-sm [overflow-wrap:anywhere]">
      <p className="font-semibold">
        Operator assessment: {value.disposition} / Evidence {value.assertion.evidence_label}
      </p>
      <p className="text-xs text-muted">
        Revision {value.number} / {formatUtc(value.created_at)} / Author {value.authored_by}
      </p>
      <p>{value.rationale}</p>
      <RelationshipFacts value={value.assertion} />
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
            <Labels labels={[row.label]} /> / {row.relation} / Original {row.excerpt.field}
          </p>
          <p>{row.excerpt.text}</p>
        </blockquote>
      ))}
    </div>
  );
}

export function RelationshipHistory({ current }: { current: RelationshipRevision }) {
  const [id, setId] = useState(current.id);
  const request = useScopedRequest();
  const loader = useCallback(
    () => fetchRelationship(current.relationship_id, id, request()),
    [current.relationship_id, id, request],
  );
  const resource = useScopedResource(loader);
  return (
    <div className="mt-4 space-y-3">
      {resource.loading && <LoadingNote label="Loading relationship revision" />}
      {resource.error && (
        <Alert tone="error">
          {describeError(resource.error)}{' '}
          <Button variant="secondary" onClick={() => void resource.reload()}>
            Retry relationship revision
          </Button>
        </Alert>
      )}
      {resource.data && (
        <>
          <RelationshipRevisionText value={resource.data.revision} />
          <RelationshipExportChoice value={resource.data.revision} />
          {resource.data.revision.previous_id && (
            <Button
              variant="secondary"
              onClick={() => {
                const previous = resource.data?.revision.previous_id;
                if (previous) setId(previous);
              }}
            >
              Previous relationship revision
            </Button>
          )}
          {id !== current.id && (
            <Button variant="secondary" onClick={() => setId(current.id)}>
              Return to opened revision {current.number}
            </Button>
          )}
        </>
      )}
    </div>
  );
}

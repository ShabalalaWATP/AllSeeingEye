import { useCallback, useState } from 'react';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { fetchClaim, listClaims } from '@/lib/api/claims';
import { ClaimEditor } from './ClaimEditor';
import { GenerateClaims } from './GenerateClaims';
import type { EvidenceItem } from '@/lib/api/reports';
import type { ClaimRevision } from '@/lib/api/claims';
import { describeError } from '@/lib/api/errors';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { formatUtc } from '@/lib/format';

interface AnnotationProps {
  reportId: string;
  version: number;
  evidence?: EvidenceItem[];
  canCreate?: boolean;
  canManage?: (root: { created_by: string; team_id: string | null }) => boolean;
}

function ExistingEditor({
  value,
  scope,
  onClose,
  onSaved,
}: {
  value: ClaimRevision;
  scope: AnnotationProps;
  onClose: () => void;
  onSaved: () => void;
}) {
  const request = useScopedRequest();
  const loader = useCallback(
    () => fetchClaim(value.claim_id, null, request()),
    [value.claim_id, request],
  );
  const resource = useScopedResource(loader);
  if (resource.loading) return <LoadingNote label="Checking claim permissions" />;
  if (resource.error) return <Alert tone="error">{describeError(resource.error)}</Alert>;
  if (!resource.data || !scope.canManage?.(resource.data.root))
    return <p className="text-sm text-muted">You can read this claim, but cannot revise it.</p>;
  return (
    <ClaimEditor
      key={`${resource.key}:${resource.data.revision.id}`}
      reportId={scope.reportId}
      version={scope.version}
      evidence={scope.evidence ?? []}
      current={resource.data.revision}
      onSaved={onSaved}
      onCancel={onClose}
    />
  );
}

function RevisionText({ value }: { value: ClaimRevision }) {
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
            {citation.label} · {citation.relation} · Original {citation.excerpt.field}
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

function ClaimHistory({ current }: { current: ClaimRevision }) {
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

function ClaimList(scope: AnnotationProps) {
  const { reportId, version } = scope;
  const [editing, setEditing] = useState<ClaimRevision | 'new' | null>(null);
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  const request = useScopedRequest();
  const loader = useCallback(
    () => listClaims(reportId, version, offset, request()),
    [reportId, version, offset, request],
  );
  const resource = useScopedResource(loader);
  return (
    <div className="mt-4 space-y-4">
      <p className="text-sm text-muted">
        Later claim annotations preserve the generated report. Reviewed means an operator reviewed
        the assertion; it is not a guarantee of truth.
      </p>
      {resource.loading && <LoadingNote label="Loading claim annotations" />}
      {resource.error && <Alert tone="error">{describeError(resource.error)}</Alert>}
      {resource.data && (
        <>
          {scope.canCreate && (
            <GenerateClaims
              key={`${resource.key}:generate`}
              reportId={reportId}
              version={version}
              onSaved={() => {
                void resource.reload();
              }}
            />
          )}
          {scope.canCreate && (
            <Button variant="secondary" onClick={() => setEditing('new')}>
              Add a claim
            </Button>
          )}
          {editing === 'new' && scope.canCreate && (
            <ClaimEditor
              key={`${resource.key}:new`}
              reportId={reportId}
              version={version}
              evidence={scope.evidence ?? []}
              onCancel={() => setEditing(null)}
              onSaved={() => {
                setEditing(null);
                void resource.reload();
              }}
            />
          )}
          {editing && editing !== 'new' && (
            <ExistingEditor
              key={`${resource.key}:${editing.id}`}
              value={editing}
              scope={scope}
              onClose={() => setEditing(null)}
              onSaved={() => {
                setEditing(null);
                void resource.reload();
              }}
            />
          )}
          {resource.data.total === 0 && (
            <p className="text-sm text-muted">No claim annotations for this report version.</p>
          )}
          {resource.data.items.map((value) => (
            <article key={value.claim_id} className="rounded border border-line p-4">
              <RevisionText value={value} />
              {scope.canCreate && (
                <Button variant="secondary" onClick={() => setEditing(value)}>
                  Review or correct claim
                </Button>
              )}
              <Button
                variant="secondary"
                className="mt-3"
                onClick={() => setSelected(selected === value.id ? null : value.id)}
              >
                Revision history
              </Button>
              {selected === value.id && (
                <ClaimHistory key={`${resource.key}:${value.id}`} current={value} />
              )}
            </article>
          ))}
          {resource.data.total > 20 && (
            <div className="flex items-center gap-3">
              <Button
                variant="secondary"
                disabled={offset === 0}
                onClick={() => setOffset(Math.max(0, offset - 20))}
              >
                Previous page
              </Button>
              <span className="text-sm">
                {offset + 1}–{offset + resource.data.items.length} of {resource.data.total}
              </span>
              <Button
                variant="secondary"
                disabled={offset + 20 >= resource.data.total}
                onClick={() => setOffset(offset + 20)}
              >
                Next page
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export function ClaimAnnotations(scope: AnnotationProps) {
  const { reportId, version } = scope;
  const [open, setOpen] = useState(false);
  return (
    <section className="rounded border border-line p-4" aria-label="Claim annotations">
      <Button variant="secondary" aria-expanded={open} onClick={() => setOpen(!open)}>
        Claim annotations and history
      </Button>
      {open && <ClaimList key={`${reportId}:${version}`} {...scope} />}
    </section>
  );
}

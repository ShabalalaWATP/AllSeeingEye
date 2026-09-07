import { useCallback, useState } from 'react';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { fetchClaim, listClaims } from '@/lib/api/claims';
import { ClaimEditor } from './ClaimEditor';
import { GenerateClaims } from './GenerateClaims';
import { ClaimGenerationNote } from './ClaimGenerationNote';
import type { ClaimGenerationReceipt } from '@/lib/api/claimGeneration';
import type { EvidenceItem } from '@/lib/api/reports';
import type { ClaimRevision } from '@/lib/api/claims';
import { describeError } from '@/lib/api/errors';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { ClaimHistory, RevisionText } from './ClaimHistory';
import { ClaimExportSelection, ClaimExportChoice } from './ClaimExportSelection';

interface AnnotationProps {
  sharedSelection?: boolean;
  generation?: ClaimGenerationReceipt | null | undefined;
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
  if (!resource.data || !scope.canManage?.(resource.data.root))
    return (
      <div className="space-y-3">
        {resource.loading ? (
          <LoadingNote label="Checking claim permissions" />
        ) : resource.error ? (
          <Alert tone="error">{describeError(resource.error)}</Alert>
        ) : (
          <p className="text-sm text-muted">You can read this claim, but cannot revise it.</p>
        )}
        <Button variant="secondary" onClick={onClose}>
          Cancel review
        </Button>
      </div>
    );
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

function ClaimList(scope: AnnotationProps) {
  const { reportId, version } = scope;
  const [editing, setEditing] = useState<ClaimRevision | 'new' | null>(null);
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const locked = editing !== null || generating;
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
              disabled={editing !== null}
              onBusyChange={setGenerating}
              onSaved={() => {
                void resource.reload();
              }}
            />
          )}
          {scope.canCreate && (
            <Button variant="secondary" disabled={locked} onClick={() => setEditing('new')}>
              Add a claim
            </Button>
          )}
          {editing !== null && (
            <p className="text-xs text-muted">
              Save or cancel your claim before switching pages, generating proposals or opening
              another editor.
            </p>
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
              <ClaimExportChoice value={value} />
              {scope.canCreate && (
                <Button variant="secondary" disabled={locked} onClick={() => setEditing(value)}>
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
                disabled={locked || offset === 0}
                onClick={() => setOffset(Math.max(0, offset - 20))}
              >
                Previous page
              </Button>
              <span className="text-sm">
                {offset + 1}–{offset + resource.data.items.length} of {resource.data.total}
              </span>
              <Button
                variant="secondary"
                disabled={locked || offset + 20 >= resource.data.total}
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
      <ClaimGenerationNote receipt={scope.generation ?? null} />
      <Button variant="secondary" aria-expanded={open} onClick={() => setOpen(!open)}>
        Claim annotations and history
      </Button>
      {open &&
        (scope.sharedSelection ? (
          <ClaimList key={`${reportId}:${version}`} {...scope} />
        ) : (
          <ClaimExportSelection reportId={reportId} version={version}>
            <ClaimList key={`${reportId}:${version}`} {...scope} />
          </ClaimExportSelection>
        ))}
    </section>
  );
}

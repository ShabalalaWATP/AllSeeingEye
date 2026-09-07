import { useCallback, useState, useSyncExternalStore } from 'react';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SelectField } from '@/components/ui/Field';
import {
  fetchRelationship,
  listRelationships,
  listRelationshipAssertions,
} from '@/lib/api/relationships';
import type { RelationshipRoot } from '@/lib/api/relationships';
import type { EvidenceItem } from '@/lib/api/reports';
import { describeError } from '@/lib/api/errors';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { subscribeWorkspaceAccess, workspaceRevision } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';
import { RelationshipFacts } from './RelationshipFacts';
import { RelationshipEditor } from './RelationshipEditor';
import { RelationshipExportChoice } from './ClaimExportSelection';
import { RelationshipHistory, RelationshipRevisionText } from './RelationshipHistory';

interface Props {
  reportId: string;
  version: number;
  evidence: EvidenceItem[];
  canCreate: boolean;
  canManage: (root: RelationshipRoot) => boolean;
}

function ExistingReview({
  relationshipId,
  scope,
  onClose,
  onSaved,
}: {
  relationshipId: string;
  scope: Props;
  onClose: () => void;
  onSaved: () => void;
}) {
  const request = useScopedRequest();
  const loader = useCallback(
    () => fetchRelationship(relationshipId, null, request()),
    [relationshipId, request],
  );
  const resource = useScopedResource(loader);
  if (!resource.data || !scope.canManage(resource.data.root))
    return (
      <div className="space-y-3">
        {resource.loading ? (
          <LoadingNote label="Checking relationship review permissions" />
        ) : resource.error ? (
          <Alert tone="error">{describeError(resource.error)}</Alert>
        ) : (
          <p className="text-sm text-muted">
            You can read this review. Its author, a manager leading this team or an administrator
            can correct it.
          </p>
        )}
        <Button variant="secondary" onClick={onClose}>
          Cancel review
        </Button>
      </div>
    );
  return (
    <RelationshipEditor
      key={resource.data.revision.id}
      reportId={scope.reportId}
      version={scope.version}
      label={resource.data.root.evidence_label}
      evidence={scope.evidence}
      current={resource.data.revision}
      onSaved={onSaved}
      onCancel={onClose}
      onReload={() => void resource.reload()}
    />
  );
}

function ReviewList(scope: Props) {
  const [offset, setOffset] = useState(0);
  const [editing, setEditing] = useState<{ relationshipId: string } | 'new' | null>(null);
  const [label, setLabel] = useState('');
  const [history, setHistory] = useState<string | null>(null);
  const request = useScopedRequest();
  const loader = useCallback(async () => {
    const signal = request();
    const [reviews, assertions] = await Promise.all([
      listRelationships(scope.reportId, scope.version, offset, signal),
      listRelationshipAssertions(scope.reportId, scope.version, signal),
    ]);
    return { ...reviews, assertions };
  }, [scope.reportId, scope.version, offset, request]);
  const resource = useScopedResource(loader);
  const saved = () => {
    setEditing(null);
    void resource.reload();
  };
  const assertions = resource.data?.assertions.items ?? [];
  const candidate = assertions.find((item) => item.evidence_label === label) ?? assertions[0];
  const selectedLabel = candidate?.evidence_label ?? '';
  const existingId = resource.data?.assertions.review_ids[selectedLabel];
  return (
    <div className="mt-4 space-y-4">
      <p className="text-sm text-muted">
        Operator decisions remain separate from captured source assertions. An assessment does not
        establish ownership, identity or current validity. Each assertion has one review history per
        report version.
      </p>
      {resource.data && assertions.length === 0 && (
        <p className="text-sm text-muted">
          No supported source-reported relationships are available for review in this version.
          Legacy or incomplete records remain readable in the evidence annex.
        </p>
      )}
      {resource.data && resource.data.assertions.unavailable_labels.length > 0 && (
        <p className="text-sm text-muted">
          Some captured records cannot be projected safely for review:{' '}
          {resource.data.assertions.unavailable_labels.join(', ')}. Consult their original evidence.
        </p>
      )}
      {resource.loading && <LoadingNote label="Loading relationship reviews" />}
      {resource.error && (
        <Alert tone="error">
          {describeError(resource.error)}{' '}
          <Button variant="secondary" onClick={() => void resource.reload()}>
            Retry relationship reviews
          </Button>
        </Alert>
      )}
      {resource.data && (
        <>
          {scope.canCreate && candidate && (
            <div className="space-y-3">
              <SelectField
                label="Captured relationship"
                value={selectedLabel}
                disabled={editing !== null}
                onChange={(event) => setLabel(event.target.value)}
                options={assertions.map((item) => ({
                  value: item.evidence_label,
                  label: `${item.evidence_label} / ${item.kind} / ${item.child_lei} to ${item.parent_lei}`,
                }))}
              />
              <Button
                variant="secondary"
                disabled={editing !== null}
                onClick={() => setEditing(existingId ? { relationshipId: existingId } : 'new')}
              >
                {existingId
                  ? 'Open existing relationship review'
                  : 'Review a captured relationship'}
              </Button>
            </div>
          )}
          {editing !== null && (
            <p className="text-xs text-muted">
              Save or cancel your review before switching assertions or pages.
            </p>
          )}
          {editing === 'new' && scope.canCreate && candidate && (
            <div className="space-y-3">
              <RelationshipFacts value={candidate} />
              <RelationshipEditor
                key={selectedLabel}
                reportId={scope.reportId}
                version={scope.version}
                label={selectedLabel}
                evidence={scope.evidence}
                onSaved={saved}
                onCancel={() => {
                  setEditing(null);
                  void resource.reload();
                }}
              />
            </div>
          )}
          {editing && editing !== 'new' && (
            <ExistingReview
              key={editing.relationshipId}
              relationshipId={editing.relationshipId}
              scope={scope}
              onSaved={saved}
              onClose={() => {
                setEditing(null);
                void resource.reload();
              }}
            />
          )}
          {resource.data.total === 0 && (
            <p className="text-sm text-muted">No operator relationship reviews for this version.</p>
          )}
          {resource.data.items.map((value) => (
            <article key={value.id} className="space-y-3 rounded border border-line p-4">
              <RelationshipRevisionText value={value} />
              <RelationshipExportChoice value={value} />
              {scope.canCreate && (
                <Button
                  variant="secondary"
                  disabled={editing !== null}
                  onClick={() => setEditing({ relationshipId: value.relationship_id })}
                >
                  Review or correct relationship
                </Button>
              )}
              <Button
                variant="secondary"
                onClick={() => setHistory(history === value.id ? null : value.id)}
              >
                Relationship revision history
              </Button>
              {history === value.id && <RelationshipHistory key={value.id} current={value} />}
            </article>
          ))}
          {resource.data.total > 20 && (
            <div className="flex gap-3">
              <Button
                variant="secondary"
                disabled={editing !== null || offset === 0}
                onClick={() => setOffset(Math.max(0, offset - 20))}
              >
                Previous reviews
              </Button>
              <span className="text-sm">
                {offset + 1} to {offset + resource.data.items.length} of {resource.data.total}
              </span>
              <Button
                variant="secondary"
                disabled={editing !== null || offset + 20 >= resource.data.total}
                onClick={() => setOffset(offset + 20)}
              >
                Next reviews
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function ReviewSection(scope: Props) {
  const [open, setOpen] = useState(false);
  return (
    <section aria-label="Relationship reviews" className="rounded border border-line p-4">
      <Button variant="secondary" aria-expanded={open} onClick={() => setOpen(!open)}>
        Relationship reviews and history
      </Button>
      {open && <ReviewList {...scope} />}
    </section>
  );
}

export function RelationshipReviews(scope: Props) {
  const actor = useAuthStore(
    (state) => `${state.status}:${state.user?.id}:${state.user?.role}:${state.user?.is_active}`,
  );
  const access = useSyncExternalStore(subscribeWorkspaceAccess, workspaceRevision);
  return <ReviewSection key={`${actor}:${access}:${scope.reportId}:${scope.version}`} {...scope} />;
}

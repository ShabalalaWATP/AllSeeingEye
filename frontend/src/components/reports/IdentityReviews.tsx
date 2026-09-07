import { useCallback, useState, useSyncExternalStore } from 'react';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SelectField } from '@/components/ui/Field';
import { fetchIdentity, listIdentities } from '@/lib/api/identities';
import type { IdentityCandidate, IdentityRevision, IdentityRoot } from '@/lib/api/identities';
import type { EvidenceItem } from '@/lib/api/reports';
import { describeError } from '@/lib/api/errors';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { subscribeWorkspaceAccess, workspaceRevision } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';
import { IdentityEditor } from './IdentityEditor';
import { IdentityExportChoice } from './ClaimExportSelection';
import { CandidateFacts, IdentityHistory, IdentityRevisionText } from './IdentityHistory';

interface Props {
  reportId: string;
  version: number;
  subject: string | null;
  candidates: IdentityCandidate[];
  evidence: EvidenceItem[];
  canCreate: boolean;
  canManage: (root: IdentityRoot) => boolean;
}

function ExistingReview({
  current,
  scope,
  onClose,
  onSaved,
}: {
  current: IdentityRevision;
  scope: Props;
  onClose: () => void;
  onSaved: () => void;
}) {
  const request = useScopedRequest();
  const loader = useCallback(
    () => fetchIdentity(current.decision_id, null, request()),
    [current.decision_id, request],
  );
  const resource = useScopedResource(loader);
  if (!resource.data || !scope.canManage(resource.data.root))
    return (
      <div className="space-y-3">
        {resource.loading ? (
          <LoadingNote label="Checking identity review permissions" />
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
    <IdentityEditor
      key={resource.data.revision.id}
      reportId={scope.reportId}
      version={scope.version}
      label={resource.data.root.candidate_label}
      subject={resource.data.root.subject}
      evidence={scope.evidence}
      current={resource.data.revision}
      onSaved={onSaved}
      onCancel={onClose}
    />
  );
}

function ReviewList(scope: Props) {
  const [offset, setOffset] = useState(0);
  const [editing, setEditing] = useState<IdentityRevision | 'new' | null>(null);
  const [label, setLabel] = useState(scope.candidates[0]?.evidence_label ?? '');
  const [history, setHistory] = useState<string | null>(null);
  const request = useScopedRequest();
  const loader = useCallback(
    () => listIdentities(scope.reportId, scope.version, offset, request()),
    [scope.reportId, scope.version, offset, request],
  );
  const resource = useScopedResource(loader);
  const saved = () => {
    setEditing(null);
    void resource.reload();
  };
  const candidate = scope.candidates.find((item) => item.evidence_label === label);
  return (
    <div className="mt-4 space-y-4">
      <p className="text-sm text-muted">
        Operator decisions remain separate from captured source assertions. A match does not merge
        records or establish ownership. Each candidate has one review history per report version.
      </p>
      {!scope.subject && (
        <p className="text-sm text-muted">
          Creating a review requires a report with an explicit company research subject.
        </p>
      )}
      {scope.candidates.length === 0 && (
        <p className="text-sm text-muted">No identity candidates were captured in this version.</p>
      )}
      {resource.loading && <LoadingNote label="Loading identity reviews" />}
      {resource.error && (
        <Alert tone="error">
          {describeError(resource.error)}{' '}
          <Button variant="secondary" onClick={() => void resource.reload()}>
            Retry identity reviews
          </Button>
        </Alert>
      )}
      {resource.data && (
        <>
          {scope.canCreate && scope.subject && candidate && (
            <div className="space-y-3">
              <SelectField
                label="Captured candidate"
                value={label}
                disabled={editing !== null}
                onChange={(event) => setLabel(event.target.value)}
                options={scope.candidates.map((item) => ({
                  value: item.evidence_label,
                  label: `${item.evidence_label} · ${item.identifiers[0]?.value ?? item.aliases[0]?.value ?? 'Captured identity'}`,
                }))}
              />
              <Button
                variant="secondary"
                disabled={editing !== null}
                onClick={() => setEditing('new')}
              >
                Review a captured identity
              </Button>
            </div>
          )}
          {editing !== null && (
            <p className="text-xs text-muted">
              Save or cancel your review before switching candidates or pages.
            </p>
          )}
          {editing === 'new' && scope.canCreate && scope.subject && candidate && (
            <div className="space-y-3">
              <CandidateFacts
                candidate={candidate}
                attributes={scope.evidence.find((item) => item.label === label)?.attributes}
              />
              <IdentityEditor
                key={label}
                reportId={scope.reportId}
                version={scope.version}
                label={label}
                subject={scope.subject}
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
              key={editing.id}
              current={editing}
              scope={scope}
              onSaved={saved}
              onClose={() => {
                setEditing(null);
                void resource.reload();
              }}
            />
          )}
          {resource.data.total === 0 && (
            <p className="text-sm text-muted">No operator identity reviews for this version.</p>
          )}
          {resource.data.items.map((value) => (
            <article key={value.id} className="space-y-3 rounded border border-line p-4">
              <IdentityRevisionText value={value} />
              <IdentityExportChoice value={value} />
              {scope.canCreate && (
                <Button
                  variant="secondary"
                  disabled={editing !== null}
                  onClick={() => setEditing(value)}
                >
                  Review or correct identity
                </Button>
              )}
              <Button
                variant="secondary"
                onClick={() => setHistory(history === value.id ? null : value.id)}
              >
                Identity revision history
              </Button>
              {history === value.id && <IdentityHistory key={value.id} current={value} />}
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
                {offset + 1}–{offset + resource.data.items.length} of {resource.data.total}
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
    <section aria-label="Identity reviews" className="rounded border border-line p-4">
      <Button variant="secondary" aria-expanded={open} onClick={() => setOpen(!open)}>
        Identity reviews and history
      </Button>
      {open && <ReviewList {...scope} />}
    </section>
  );
}

export function IdentityReviews(scope: Props) {
  const user = useAuthStore((state) => state.user);
  const access = useSyncExternalStore(subscribeWorkspaceAccess, workspaceRevision);
  return (
    <ReviewSection
      key={`${user?.id}:${user?.role}:${user?.is_active}:${access}:${scope.reportId}:${scope.version}`}
      {...scope}
    />
  );
}

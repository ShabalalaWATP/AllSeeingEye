import { createContext, useContext, useState, useSyncExternalStore } from 'react';
import type { ReactNode } from 'react';
import { Button } from '@/components/ui/Button';
import { Alert } from '@/components/ui/Alert';
import type { ClaimRevision } from '@/lib/api/claims';
import type { IdentityRevision } from '@/lib/api/identities';
import { fetchClaimPackage } from '@/lib/api/claimExport';
import { describeError } from '@/lib/api/errors';
import { saveBinaryFile } from '@/lib/downloadBinary';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { subscribeWorkspaceAccess, workspaceRevision } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';

type SelectedRevision = ClaimRevision | IdentityRevision;
const isClaim = (value: SelectedRevision): value is ClaimRevision => 'claim_id' in value;
const selectionKey = (value: SelectedRevision) =>
  `${isClaim(value) ? 'claim' : 'identity'}:${value.id}`;
const selectionTitle = (value: SelectedRevision) =>
  isClaim(value)
    ? value.statement
    : `${value.subject} · Candidate ${value.candidate.candidate.evidence_label}`;

interface SelectionContext {
  values: SelectedRevision[];
  busy: boolean;
  toggle: (value: SelectedRevision) => void;
}
const Selection = createContext<SelectionContext | null>(null);

export function ClaimExportChoice({ value }: { value: ClaimRevision }) {
  return <ExportChoice value={value} />;
}

export function IdentityExportChoice({ value }: { value: IdentityRevision }) {
  return <ExportChoice value={value} />;
}

function ExportChoice({ value }: { value: SelectedRevision }) {
  const selection = useContext(Selection);
  if (!selection) return null;
  const checked = selection.values.some((item) => selectionKey(item) === selectionKey(value));
  return (
    <label className="my-3 flex items-center gap-2 text-sm">
      <input
        type="checkbox"
        checked={checked}
        disabled={selection.busy || (!checked && selection.values.length >= 20)}
        onChange={() => selection.toggle(value)}
      />
      Include {isClaim(value) ? '' : 'identity '}revision {value.number} in evidence package
    </label>
  );
}

interface Props {
  reportId: string;
  version: number;
  children: ReactNode;
}

function SelectionBody({ reportId, version, children }: Props) {
  const [values, setValues] = useState<SelectedRevision[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const request = useScopedRequest();
  const toggle = (value: SelectedRevision) => {
    if (busy) return;
    setValues((previous) =>
      previous.some((item) => selectionKey(item) === selectionKey(value))
        ? previous.filter((item) => selectionKey(item) !== selectionKey(value))
        : previous.length < 20
          ? [...previous, value]
          : previous,
    );
  };
  const identities = values.filter((value): value is IdentityRevision => !isClaim(value));
  const download = async () => {
    if (busy || values.length === 0) return;
    const signal = request();
    setBusy(true);
    setError(null);
    try {
      const blob = await fetchClaimPackage(
        reportId,
        {
          version_number: version,
          revisions: values
            .filter(isClaim)
            .map((value) => ({ claim_id: value.claim_id, revision_id: value.id })),
          ...(identities.length > 0
            ? {
                identity_revisions: identities.map((value) => ({
                  decision_id: value.decision_id,
                  revision_id: value.id,
                })),
              }
            : {}),
        },
        signal,
      );
      if (!signal.aborted)
        saveBinaryFile(
          `report-v${String(version)}-selected-${identities.length > 0 ? 'annotations' : 'claims'}.zip`,
          blob,
        );
    } catch (caught) {
      if (!signal.aborted) setError(caught);
    } finally {
      if (!signal.aborted) setBusy(false);
    }
  };
  return (
    <Selection.Provider value={{ values, busy, toggle }}>
      <div
        className="mt-4 space-y-3 rounded border border-line p-4"
        aria-label="Selected evidence package"
      >
        <h3 className="font-medium">Build an evidence package</h3>
        <p className="text-sm text-muted">
          Choose up to 20 exact revisions from claims, identity reviews or their history. The ZIP
          includes this frozen report and your selected revisions, with excerpts and integrity
          hashes. Original source files are not included.
        </p>
        <p className="text-sm" role="status">
          {values.length} of 20 revisions selected
        </p>
        {values.length > 0 && (
          <ul className="space-y-2 text-sm">
            {values.map((value) => (
              <li
                key={selectionKey(value)}
                className="flex items-start justify-between gap-3 [overflow-wrap:anywhere]"
              >
                <span>
                  {selectionTitle(value)} · Revision {value.number} ·{' '}
                  {isClaim(value) ? value.state : value.disposition}
                </span>
                <Button
                  variant="secondary"
                  disabled={busy}
                  onClick={() => toggle(value)}
                  aria-label={`Remove ${isClaim(value) ? '' : 'identity '}revision ${String(value.number)}: ${selectionTitle(value)}`}
                >
                  Remove
                </Button>
              </li>
            ))}
          </ul>
        )}
        <div className="flex flex-wrap gap-2">
          <Button
            variant="secondary"
            busy={busy}
            disabled={values.length === 0}
            onClick={() => void download()}
          >
            {identities.length > 0 ? 'Download selected evidence' : 'Download selected claims'}
          </Button>
          <Button
            variant="secondary"
            disabled={busy || values.length === 0}
            onClick={() => setValues([])}
          >
            Clear selection
          </Button>
        </div>
        {error !== null && <Alert tone="error">{describeError(error)}</Alert>}
      </div>
      {children}
    </Selection.Provider>
  );
}

export function ClaimExportSelection(props: Props) {
  const actor = useAuthStore(
    (state) => `${state.status}:${state.user?.id}:${state.user?.role}:${state.user?.is_active}`,
  );
  const access = useSyncExternalStore(subscribeWorkspaceAccess, workspaceRevision);
  return (
    <SelectionBody
      key={`${actor}:${String(access)}:${props.reportId}:${String(props.version)}`}
      {...props}
    />
  );
}

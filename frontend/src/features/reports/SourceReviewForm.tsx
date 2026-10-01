import { useId } from 'react';

import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import {
  AUTHENTICITY_LABELS,
  CREDIBILITY_LABELS,
  RELIABILITY_LABELS,
  type Authenticity,
  type Credibility,
  type Reliability,
  type SourceReviewKind,
} from '@/lib/api/sourceReviews';

export interface ReviewDraft {
  reliability: Reliability | '';
  credibility: Credibility | '';
  authenticity: Authenticity | '';
  basis: string;
  expertiseBasis: string;
  policyNote: string;
}

export const EMPTY_DRAFT: ReviewDraft = {
  reliability: '',
  credibility: '',
  authenticity: '',
  basis: '',
  expertiseBasis: '',
  policyNote: '',
};

export function draftComplete(kind: SourceReviewKind, draft: ReviewDraft): boolean {
  const grade =
    kind === 'reliability'
      ? draft.reliability
      : kind === 'credibility'
        ? draft.credibility
        : draft.authenticity;
  return grade !== '' && draft.basis.trim().length > 0;
}

const field = 'w-full rounded border border-line bg-surface p-2 text-sm text-text';

/** The grade each kind requires, its basis and optional notes. The draft is owned above. */
export function SourceReviewForm({
  kind,
  draft,
  onChange,
  correcting,
  busy,
  error,
  onSubmit,
  onReload,
}: {
  kind: SourceReviewKind;
  draft: ReviewDraft;
  onChange: (draft: ReviewDraft) => void;
  correcting: boolean;
  busy: boolean;
  error: { message: string; stale: boolean } | null;
  onSubmit: () => void;
  onReload: () => void;
}) {
  const id = useId();
  const set = (changes: Partial<ReviewDraft>) => onChange({ ...draft, ...changes });
  return (
    <form
      className="space-y-2"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      {kind === 'reliability' && (
        <>
          <label className="block text-xs" htmlFor={`${id}-reliability`}>
            Reliability grade
          </label>
          <select
            id={`${id}-reliability`}
            className={field}
            value={draft.reliability}
            onChange={(event) => set({ reliability: event.target.value as Reliability | '' })}
          >
            <option value="">Choose a grade</option>
            {Object.entries(RELIABILITY_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
          <label className="block text-xs" htmlFor={`${id}-expertise`}>
            Expertise basis (optional)
          </label>
          <textarea
            id={`${id}-expertise`}
            className={field}
            rows={2}
            maxLength={1000}
            value={draft.expertiseBasis}
            onChange={(event) => set({ expertiseBasis: event.target.value })}
          />
        </>
      )}
      {kind === 'credibility' && (
        <>
          <label className="block text-xs" htmlFor={`${id}-credibility`}>
            Credibility grade
          </label>
          <select
            id={`${id}-credibility`}
            className={field}
            value={String(draft.credibility)}
            onChange={(event) =>
              set({
                credibility: event.target.value ? (Number(event.target.value) as Credibility) : '',
              })
            }
          >
            <option value="">Choose a grade</option>
            {Object.entries(CREDIBILITY_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </>
      )}
      {kind === 'authenticity' && (
        <>
          <label className="block text-xs" htmlFor={`${id}-authenticity`}>
            Issuer authenticity
          </label>
          <select
            id={`${id}-authenticity`}
            className={field}
            value={draft.authenticity}
            onChange={(event) => set({ authenticity: event.target.value as Authenticity | '' })}
          >
            <option value="">Choose a status</option>
            {Object.entries(AUTHENTICITY_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </>
      )}
      <label className="block text-xs" htmlFor={`${id}-basis`}>
        Basis (required, up to 1,000 characters)
      </label>
      <textarea
        id={`${id}-basis`}
        className={field}
        rows={3}
        maxLength={1000}
        value={draft.basis}
        onChange={(event) => set({ basis: event.target.value })}
      />
      <label className="block text-xs" htmlFor={`${id}-policy`}>
        Policy note (optional; required by the server when the assessment policy changed)
      </label>
      <textarea
        id={`${id}-policy`}
        className={field}
        rows={2}
        maxLength={1000}
        value={draft.policyNote}
        onChange={(event) => set({ policyNote: event.target.value })}
      />
      {error && (
        <Alert tone="error">
          {error.message}
          {error.stale &&
            ' Your draft is kept. Reload the history, check the newer revision, then submit again.'}
        </Alert>
      )}
      <div className="flex flex-wrap gap-2">
        <Button
          type="submit"
          variant="secondary"
          busy={busy}
          disabled={!draftComplete(kind, draft)}
        >
          {correcting ? 'Record correction' : 'Record review'}
        </Button>
        {error?.stale && (
          <Button variant="ghost" onClick={onReload}>
            Reload history
          </Button>
        )}
      </div>
    </form>
  );
}

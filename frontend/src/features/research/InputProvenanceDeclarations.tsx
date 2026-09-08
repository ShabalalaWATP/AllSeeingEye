import { useEffect, useState } from 'react';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SourceProvenanceDetails } from '@/components/reports/SourceProvenanceDetails';
import { fetchDeclarationTargets, declareInputProvenance } from '@/lib/api/inputDeclarations';
import type { DeclarationTargets, InputDeclarations } from '@/lib/api/inputDeclarations';
import type { ResearchInputReceipt } from '@/lib/api/researchInputs';
import { ApiError, describeError } from '@/lib/api/errors';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import {
  InputDeclarationFields,
  emptyDeclaration,
  type DeclarationDraft,
} from './InputDeclarationFields';

export function InputProvenanceDeclarations({
  receipt,
  disabled,
  onReplace,
  onBusy,
}: {
  receipt: ResearchInputReceipt;
  disabled: boolean;
  onReplace: (receipt: ResearchInputReceipt) => void;
  onBusy: (busy: boolean) => void;
}) {
  const request = useScopedRequest();
  const [targets, setTargets] = useState<DeclarationTargets | null>(null);
  const [drafts, setDrafts] = useState<DeclarationDraft[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    onBusy(busy);
    return () => onBusy(false);
  }, [busy, onBusy]);
  const load = async () => {
    if (busy || disabled) return;
    const signal = request();
    setBusy(true);
    setError(null);
    try {
      const value = await fetchDeclarationTargets(receipt.id, signal);
      if (signal.aborted) return;
      if (
        value.input_id !== receipt.id ||
        value.sha256 !== receipt.sha256 ||
        Date.parse(value.expires_at) <= Date.now()
      )
        throw new ApiError(
          422,
          'invalid_request',
          'The declaration targets no longer match this attachment. Import it again.',
        );
      setTargets(value);
    } catch (caught) {
      if (!signal.aborted) setError(describeError(caught));
    } finally {
      if (!signal.aborted) setBusy(false);
    }
  };
  const save = async () => {
    if (busy || disabled || !targets || !drafts.length || receipt.parent_input_id) return;
    let declarations: InputDeclarations['declarations'];
    try {
      declarations = drafts.map((draft) => {
        const target = targets.targets.find((row) => row.event_id === draft.eventId);
        const original = target?.[draft.field];
        if (!target || !original || (!draft.transform && !draft.date))
          throw new ApiError(
            422,
            'invalid_request',
            'Choose a non-empty original field and at least one declaration for each passage.',
          );
        if (
          draft.transform &&
          (!draft.transformed.trim() || !draft.method.trim() || original.length > 2000)
        )
          throw new ApiError(
            422,
            'invalid_request',
            'Text transformations need a whole original field up to 2,000 characters, transformed text and a method.',
          );
        if (draft.date && (!draft.rawDate || !original.includes(draft.rawDate)))
          throw new ApiError(
            422,
            'invalid_request',
            'The raw date must appear exactly in the selected original field.',
          );
        return {
          event_id: target.event_id,
          content_hash: target.content_hash,
          transformations: draft.transform
            ? [
                {
                  field: draft.field,
                  original_text: original,
                  transformed_text: draft.transformed,
                  kind: draft.kind,
                  source_language: draft.sourceLanguage,
                  target_language: draft.targetLanguage,
                  method: draft.method,
                  ...(draft.sourceScript ? { source_script: draft.sourceScript } : {}),
                  ...(draft.targetScript ? { target_script: draft.targetScript } : {}),
                },
              ]
            : [],
          source_dates: draft.date
            ? [
                {
                  field: draft.field,
                  raw_text: draft.rawDate,
                  role: draft.role,
                  calendar: draft.calendar,
                },
              ]
            : [],
        };
      });
      const grouped = new Map<string, InputDeclarations['declarations'][number]>();
      for (const declaration of declarations) {
        const existing = grouped.get(declaration.event_id);
        if (existing) {
          existing.transformations = [
            ...(existing.transformations ?? []),
            ...(declaration.transformations ?? []),
          ];
          existing.source_dates = [
            ...(existing.source_dates ?? []),
            ...(declaration.source_dates ?? []),
          ];
        } else grouped.set(declaration.event_id, declaration);
      }
      declarations = [...grouped.values()];
      for (const declaration of declarations) {
        const target = targets.targets.find((row) => row.event_id === declaration.event_id);
        if (
          !target ||
          (declaration.transformations?.length ?? 0) + target.transformations.length > 4 ||
          (declaration.source_dates?.length ?? 0) + target.source_dates.length > 4
        )
          throw new ApiError(
            422,
            'invalid_request',
            'Use up to four text transformations and four source dates per passage, including retained source metadata.',
          );
      }
    } catch (caught) {
      setError(describeError(caught));
      return;
    }
    const signal = request();
    setBusy(true);
    setError(null);
    try {
      const value = await declareInputProvenance(
        receipt.id,
        { sha256: receipt.sha256, declarations },
        signal,
      );
      if (signal.aborted) return;
      if (
        value.sha256 !== receipt.sha256 ||
        value.id === receipt.id ||
        value.parent_input_id !== receipt.id ||
        Date.parse(value.expires_at) <= Date.now()
      )
        throw new ApiError(
          422,
          'invalid_request',
          'The declared attachment response could not be verified. Import the file again.',
        );
      onReplace(value);
    } catch (caught) {
      if (!signal.aborted) setError(describeError(caught));
    } finally {
      if (!signal.aborted) setBusy(false);
    }
  };
  return (
    <details className="space-y-3 border-t border-line pt-3">
      <summary className="cursor-pointer text-sm font-medium">
        Declare source language or calendar
      </summary>
      <p className="text-xs text-muted">
        Add your own translation, transliteration or calendar declaration to selected extracted
        passages. Original text stays unchanged. Saving creates a separate temporary attachment for
        this run; earlier reports are unchanged. This uses a second private input slot and no public
        source requests.
      </p>
      <Button variant="secondary" disabled={disabled} busy={busy} onClick={() => void load()}>
        {targets ? 'Refresh original passages' : 'Load original passages'}
      </Button>
      {busy && (
        <Button
          variant="ghost"
          onClick={() => {
            request();
            setBusy(false);
            setError('Declaration request cancelled. The original attachment remains selected.');
          }}
        >
          Cancel declaration request
        </Button>
      )}
      {error && <Alert tone="error">{error}</Alert>}
      {receipt.parent_input_id && (
        <p className="text-xs text-muted">
          This attachment contains saved declarations and is available for inspection only. To
          correct them, remove this attachment and import the original file again once a private
          input slot is available.
        </p>
      )}
      {targets && (
        <fieldset disabled={busy || disabled} className="space-y-3">
          {targets.targets
            .filter((target) => target.transformations.length || target.source_dates.length)
            .map((target) => (
              <section key={target.event_id}>
                <h4 className="text-sm">{target.title}</h4>
                <p className="text-xs text-muted">
                  Recorded provenance, read-only. These rows remain unchanged when you add
                  declarations.
                </p>
                <SourceProvenanceDetails
                  transformations={target.transformations}
                  dates={target.source_dates}
                />
              </section>
            ))}
          {!receipt.parent_input_id && (
            <>
              {drafts.map((draft, index) => (
                <div key={index} className="space-y-2">
                  <InputDeclarationFields
                    value={draft}
                    targets={targets.targets}
                    index={index}
                    update={(value) =>
                      setDrafts((current) =>
                        current.map((row, position) => (position === index ? value : row)),
                      )
                    }
                  />
                  <Button
                    variant="ghost"
                    onClick={() =>
                      setDrafts((current) => current.filter((_, position) => position !== index))
                    }
                  >
                    Remove declaration {index + 1}
                  </Button>
                </div>
              ))}
              <Button
                variant="secondary"
                disabled={drafts.length >= 8 || targets.targets.length === 0}
                onClick={() => setDrafts((current) => [...current, emptyDeclaration()])}
              >
                Add passage declaration
              </Button>
              <Button disabled={!drafts.length} onClick={() => void save()}>
                Save declarations for this research
              </Button>
              <p className="text-xs text-muted">
                Up to eight declaration rows. Choose the same passage again to supply another
                transformation or date, with up to four of each per passage including retained
                source metadata. Saved declarations remain unverified operator assertions. Load the
                new attachment's original passages to inspect converted dates and unresolved values
                before research.
              </p>
            </>
          )}
        </fieldset>
      )}
    </details>
  );
}

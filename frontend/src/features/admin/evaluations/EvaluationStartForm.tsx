import { useState } from 'react';

import { Button } from '@/components/ui/Button';
import { SelectField, TextField } from '@/components/ui/Field';
import type { EvaluationCatalogue, EvaluationStart } from '@/lib/api/evaluations';
import type { LlmProfile } from '@/lib/api/llm';

import { estimateCalls, parseCallCap, suggestedCallCap } from './evaluationPresentation';

const CASEBOOKS = [
  { id: 'core', title: 'Core failure modes' },
  { id: 'regional', title: 'Regional seeds' },
] as const;

/** Choose a connection, a case subset and a call cap; the estimate is shown before starting. */
export function EvaluationStartForm({
  catalogue,
  profiles,
  busy,
  running,
  onStart,
}: {
  catalogue: EvaluationCatalogue;
  profiles: readonly LlmProfile[];
  busy: boolean;
  running: boolean;
  onStart: (body: EvaluationStart) => Promise<boolean>;
}) {
  const [profileId, setProfileId] = useState(profiles[0]?.id ?? '');
  const [selected, setSelected] = useState<ReadonlySet<string>>(new Set());
  // Until the administrator edits it, the cap follows the estimate for the selection.
  const [cap, setCap] = useState<string | null>(null);
  const estimate = estimateCalls(selected.size, catalogue.calls_per_case);
  const capText =
    cap ?? String(suggestedCallCap(selected.size, catalogue.calls_per_case, catalogue.max_calls));
  const parsedCap = parseCallCap(capText, catalogue.max_calls);
  const capError =
    parsedCap === null ? `Enter a whole number from 1 to ${catalogue.max_calls}.` : undefined;
  const ready = profileId !== '' && selected.size > 0 && parsedCap !== null && !running;

  function toggle(ids: readonly string[], on: boolean) {
    setSelected((current) => {
      const next = new Set(current);
      for (const id of ids) {
        if (on) next.add(id);
        else next.delete(id);
      }
      return next;
    });
  }

  async function submit() {
    if (!ready) return;
    const started = await onStart({
      profile_id: profileId,
      case_ids: catalogue.cases.filter((item) => selected.has(item.id)).map((item) => item.id),
      max_calls: parsedCap,
    });
    if (started) {
      setSelected(new Set());
      setCap(null);
    }
  }

  return (
    <form
      className="grid gap-4"
      onSubmit={(event) => {
        event.preventDefault();
        void submit();
      }}
    >
      <SelectField
        label="AI connection"
        value={profileId}
        disabled={busy || profiles.length === 0}
        hint="Saved connections configured for assessment. Its key stays on the server."
        options={
          profiles.length === 0
            ? [{ value: '', label: 'No assessment connection is configured' }]
            : profiles.map((profile) => ({
                value: profile.id,
                label: `${profile.name} · ${profile.model}`,
              }))
        }
        onChange={(event) => setProfileId(event.target.value)}
      />
      <div className="grid gap-4 md:grid-cols-2">
        {CASEBOOKS.map((book) => {
          const cases = catalogue.cases.filter((item) => item.casebook === book.id);
          const ids = cases.map((item) => item.id);
          const all = ids.length > 0 && ids.every((id) => selected.has(id));
          return (
            <fieldset key={book.id} className="grid gap-2 border border-line p-3">
              <legend className="px-1 text-sm font-semibold">{book.title}</legend>
              <label className="flex items-center gap-2 text-sm text-muted">
                <input
                  type="checkbox"
                  checked={all}
                  disabled={busy}
                  onChange={(event) => toggle(ids, event.target.checked)}
                />
                Select every {book.id} case
              </label>
              {cases.map((item) => (
                <label key={item.id} className="flex items-start gap-2 text-sm">
                  <input
                    type="checkbox"
                    className="mt-1"
                    checked={selected.has(item.id)}
                    disabled={busy}
                    onChange={(event) => toggle([item.id], event.target.checked)}
                  />
                  <span className="grid">
                    {item.title}
                    <span className="font-mono text-2xs text-muted">{item.id}</span>
                  </span>
                </label>
              ))}
            </fieldset>
          );
        })}
      </div>
      <div className="grid items-end gap-4 sm:grid-cols-2">
        <TextField
          label="Call cap"
          inputMode="numeric"
          value={capText}
          disabled={busy}
          error={capError}
          hint="The run stops when this many calls have been reserved, including failed calls."
          onChange={(event) => setCap(event.target.value)}
        />
        <p className="text-sm" aria-live="polite">
          <span className="font-semibold">Expected usage (estimate): </span>
          {selected.size} {selected.size === 1 ? 'case' : 'cases'} × {catalogue.calls_per_case}{' '}
          calls = {estimate} calls
        </p>
      </div>
      <p className="text-xs text-muted">{catalogue.estimate_notice}</p>
      <div>
        <Button type="submit" disabled={!ready} busy={busy}>
          Start evaluation
        </Button>
        {running ? (
          <span className="ml-3 text-sm text-muted">One run at a time: wait or cancel it.</span>
        ) : null}
      </div>
    </form>
  );
}

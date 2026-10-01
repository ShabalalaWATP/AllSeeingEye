import { Button } from '@/components/ui/Button';
import { TextField } from '@/components/ui/Field';

import {
  emptyPir,
  emptySir,
  PLAN_LIMITS,
  pirCode,
  sirCode,
  type PirDraft,
  type PlanErrors,
  type SirDraft,
} from './planDraft';

/** Repeatable PIR groups, each with repeatable SIR rows, within the domain limits. */
export function PlanRequirementsEditor({
  pirs,
  errors,
  onChange,
}: {
  pirs: readonly PirDraft[];
  errors: PlanErrors;
  onChange: (next: PirDraft[]) => void;
}) {
  const setPir = (index: number, patch: Partial<PirDraft>) =>
    onChange(pirs.map((pir, position) => (position === index ? { ...pir, ...patch } : pir)));
  const setSir = (pirIndex: number, sirIndex: number, patch: Partial<SirDraft>) => {
    const pir = pirs[pirIndex];
    if (!pir) return;
    setPir(pirIndex, {
      sirs: pir.sirs.map((sir, position) => (position === sirIndex ? { ...sir, ...patch } : sir)),
    });
  };
  return (
    <fieldset className="flex flex-col gap-4">
      <legend className="text-sm font-medium text-text">Requirements</legend>
      <p className="text-xs text-muted">
        Codes follow position. Removing or reordering a requirement renumbers the ones after it for
        future evidence, map matches and research. Saved reports keep the codes they were written
        with.
      </p>
      {errors.pirs === undefined ? null : (
        <p role="alert" className="text-sm text-critical">
          {errors.pirs}
        </p>
      )}
      {pirs.map((pir, pirIndex) => (
        <section
          key={pir.key}
          aria-label={pirCode(pirIndex)}
          className="flex flex-col gap-3 rounded-card border border-line p-3"
        >
          <div className="flex flex-wrap items-end gap-2">
            <div className="min-w-0 flex-1">
              <TextField
                label={`${pirCode(pirIndex)} priority intelligence requirement`}
                hint="The question this part of the plan serves, as one sentence."
                value={pir.text}
                maxLength={PLAN_LIMITS.text}
                error={errors[`pirs.${pirIndex}.text`]}
                onChange={(event) => setPir(pirIndex, { text: event.target.value })}
              />
            </div>
            <Button
              variant="ghost"
              disabled={pirs.length <= 1}
              onClick={() => onChange(pirs.filter((_, position) => position !== pirIndex))}
            >
              Remove {pirCode(pirIndex)}
            </Button>
          </div>
          {errors[`pirs.${pirIndex}.sirs`] === undefined ? null : (
            <p role="alert" className="text-sm text-critical">
              {errors[`pirs.${pirIndex}.sirs`]}
            </p>
          )}
          {pir.sirs.map((sir, sirIndex) => {
            const code = sirCode(pirIndex, sirIndex);
            const path = `pirs.${pirIndex}.sirs.${sirIndex}`;
            return (
              <div
                key={sir.key}
                role="group"
                aria-label={code}
                className="grid gap-2 border-l border-line pl-3 md:grid-cols-[2fr_1fr_1fr_auto] md:items-end"
              >
                <TextField
                  label={`${code} specific requirement`}
                  value={sir.text}
                  maxLength={PLAN_LIMITS.text}
                  error={errors[`${path}.text`]}
                  onChange={(event) => setSir(pirIndex, sirIndex, { text: event.target.value })}
                />
                <TextField
                  label={`${code} keywords`}
                  hint="Comma separated."
                  value={sir.keywords}
                  error={errors[`${path}.keywords`]}
                  onChange={(event) => setSir(pirIndex, sirIndex, { keywords: event.target.value })}
                />
                <TextField
                  label={`${code} categories`}
                  hint="Comma separated, such as conflict, news."
                  value={sir.categories}
                  error={errors[`${path}.categories`]}
                  onChange={(event) =>
                    setSir(pirIndex, sirIndex, { categories: event.target.value })
                  }
                />
                <Button
                  variant="ghost"
                  onClick={() =>
                    setPir(pirIndex, {
                      sirs: pir.sirs.filter((_, position) => position !== sirIndex),
                    })
                  }
                >
                  Remove {code}
                </Button>
              </div>
            );
          })}
          <div>
            <Button
              variant="secondary"
              disabled={pir.sirs.length >= PLAN_LIMITS.sirs}
              onClick={() => setPir(pirIndex, { sirs: [...pir.sirs, emptySir()] })}
            >
              Add specific requirement to {pirCode(pirIndex)}
            </Button>
          </div>
        </section>
      ))}
      <div>
        <Button
          variant="secondary"
          disabled={pirs.length >= PLAN_LIMITS.pirs}
          onClick={() => onChange([...pirs, emptyPir()])}
        >
          Add priority intelligence requirement
        </Button>
      </div>
    </fieldset>
  );
}

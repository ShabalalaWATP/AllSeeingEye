/** The short research form: a question, where and when, and the way into every other step. */
import { CountryMultiSelect } from '@/components/research/CountryMultiSelect';
import { RESEARCH_DEPTHS } from '@/components/research/ResearchDepth';
import { Step } from '@/components/research/FormStep';
import { Button } from '@/components/ui/Button';
import { TextAreaField } from '@/components/ui/Field';
import type { Country } from '@/lib/api/geoSchemas';

import type { ResearchDraft } from './researchRequest';
import { ResearchTimeScope } from './ResearchTimeScope';

export const ADVANCED_OPTIONS_ID = 'research-advanced-options';

type Patch = (changes: Partial<ResearchDraft>) => void;

export function ResearchQuestionField({ draft, patch }: { draft: ResearchDraft; patch: Patch }) {
  return (
    <TextAreaField
      label="Your question"
      value={draft.question}
      onChange={(event) => patch({ question: event.target.value })}
      maxLength={1000}
      required
      rows={3}
      placeholder="What has changed, what does it mean, and what should I watch next?"
      className="min-h-28 resize-y bg-surface p-4 text-base leading-relaxed transition-colors focus:border-ember motion-reduce:transition-none"
    />
  );
}

export function ResearchQuickSteps({
  draft,
  patch,
  countries,
}: {
  draft: ResearchDraft;
  patch: Patch;
  countries: readonly Country[];
}) {
  return (
    <>
      <Step
        number={1}
        title="What to ask"
        lead="Any topic: a conflict, a market, an organisation, a technology or a place."
        id="research-question"
      >
        <ResearchQuestionField draft={draft} patch={patch} />
      </Step>
      <Step
        number={2}
        title="Where and when"
        lead="Choose nations, or leave them empty for the whole world, and how far back to search."
        id="research-quick-scope"
      >
        <CountryMultiSelect
          label="Nations"
          countries={countries}
          value={draft.countries}
          onChange={(value) => patch({ countries: value })}
        />
        <ResearchTimeScope
          windowHours={draft.windowHours}
          setWindowHours={(windowHours) => patch({ windowHours })}
          dates={draft.dates}
          setDates={(dates) => patch({ dates })}
        />
      </Step>
    </>
  );
}

/** A disclosure: the full form's steps follow it, so focus stays put when it opens. */
export function AdvancedOptionsToggle({
  open,
  draft,
  onToggle,
}: {
  open: boolean;
  draft: ResearchDraft;
  onToggle: () => void;
}) {
  const depth = RESEARCH_DEPTHS.find((item) => item.value === draft.mode)?.label ?? draft.mode;
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
      <Button
        variant="secondary"
        className="min-h-11 px-4"
        aria-expanded={open}
        aria-controls={open ? ADVANCED_OPTIONS_ID : undefined}
        onClick={onToggle}
      >
        Advanced options
        <span aria-hidden="true">{open ? '▴' : '▾'}</span>
      </Button>
      <p className="text-xs leading-5 text-muted">
        {open
          ? 'Every research step is shown. Hiding them keeps the choices you made.'
          : `Research depth: ${depth}. Search languages: ${draft.languages.length}. Regions, themes, sources, where to save and report style are in advanced options.`}
      </p>
    </div>
  );
}

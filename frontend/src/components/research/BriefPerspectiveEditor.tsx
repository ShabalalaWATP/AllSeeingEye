import { SelectField, TextAreaField, TextField } from '@/components/ui/Field';
import type { BriefDraft } from '@/lib/api/researchBriefSchema';

import { BriefListField } from './BriefListField';

export function BriefPerspectiveEditor({
  draft,
  change,
}: {
  draft: BriefDraft;
  change: (next: BriefDraft) => void;
}) {
  const { lens, output, collection } = draft;
  const setLens = (patch: Partial<typeof lens>) =>
    change({ ...draft, lens: { ...lens, ...patch } });
  const setOutput = (patch: Partial<typeof output>) =>
    change({ ...draft, output: { ...output, ...patch } });
  const setCollection = (patch: Partial<typeof collection>) =>
    change({ ...draft, collection: { ...collection, ...patch } });
  return (
    <fieldset className="min-w-0 grid gap-4 border-t border-line pt-4 sm:grid-cols-2">
      <legend className="px-1 text-sm font-semibold">Lens and output</legend>
      <SelectField
        label="Analytic lens"
        value={lens.id}
        onChange={(event) => setLens({ id: event.target.value as typeof lens.id })}
        options={[
          { value: 'general', label: 'General' },
          { value: 'uk_policy', label: 'UK policy' },
          { value: 'civilian_protection', label: 'Civilian protection' },
          { value: 'regional_security', label: 'Regional security' },
          { value: 'economic_exposure', label: 'Economic exposure' },
          { value: 'energy_security', label: 'Energy security' },
          { value: 'supply_chain', label: 'Supply chain' },
          { value: 'defensive_cyber', label: 'Defensive cyber' },
          { value: 'actor_perspective', label: 'Actor perspective' },
        ]}
      />

      <TextField
        label="Audience"
        maxLength={1000}
        value={lens.audience ?? ''}
        onChange={(event) => setLens({ audience: event.target.value || null })}
      />
      <TextField
        label="Decision need"
        maxLength={1000}
        value={lens.decision_need ?? ''}
        onChange={(event) => setLens({ decision_need: event.target.value || null })}
      />
      <TextAreaField
        label="Relevance instructions"
        maxLength={1000}
        value={lens.relevance_instructions ?? ''}
        onChange={(event) => setLens({ relevance_instructions: event.target.value || null })}
      />
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={lens.challenge_conclusions}
          onChange={(event) => setLens({ challenge_conclusions: event.target.checked })}
        />
        Challenge conclusions against contrary evidence
      </label>
      <TextField
        label="Report language"
        value={output.language}
        onChange={(event) => setOutput({ language: event.target.value })}
      />
      <SelectField
        label="Report style"
        value={output.style}
        onChange={(event) => setOutput({ style: event.target.value as typeof output.style })}
        options={[
          { value: 'assessment', label: 'Assessment' },
          { value: 'briefing', label: 'Briefing' },
        ]}
      />
      <SelectField
        label="Charts"
        value={output.chart_preference}
        onChange={(event) =>
          setOutput({ chart_preference: event.target.value as typeof output.chart_preference })
        }
        options={['auto', 'prefer', 'avoid'].map((value) => ({ value, label: value }))}
      />
      <SelectField
        label="Tables"
        value={output.table_preference}
        onChange={(event) =>
          setOutput({ table_preference: event.target.value as typeof output.table_preference })
        }
        options={['auto', 'prefer', 'avoid'].map((value) => ({ value, label: value }))}
      />
      <BriefListField
        label="Preferred section IDs, comma separated"
        values={output.preferred_sections}
        change={(preferred_sections) => setOutput({ preferred_sections })}
      />
      <BriefListField
        label="Collection languages, comma separated"
        values={collection.languages}
        change={(languages) => setCollection({ languages })}
      />
    </fieldset>
  );
}

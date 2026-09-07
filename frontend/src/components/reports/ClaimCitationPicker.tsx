import { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { SelectField, TextAreaField } from '@/components/ui/Field';
import type { ClaimCreate } from '@/lib/api/claims';
import type { EvidenceItem } from '@/lib/api/reports';
import { selectedTextareaExcerpt } from './claimExcerpt';

type Citation = ClaimCreate['citations'][number];
export function ClaimCitationPicker({
  evidence,
  onAdd,
}: {
  evidence: EvidenceItem[];
  onAdd: (citation: Citation) => void;
}) {
  const [label, setLabel] = useState(evidence[0]?.label ?? '');
  const [field, setField] = useState<'title' | 'summary'>('title');
  const [relation, setRelation] = useState<Citation['relation']>('supporting');
  const [selection, setSelection] = useState<ReturnType<typeof selectedTextareaExcerpt>>(null);
  const item = evidence.find((row) => row.label === label);
  const text = item?.[field] ?? '';
  return (
    <fieldset className="space-y-3 rounded border border-line p-3">
      <legend className="text-sm font-medium">Add evidence excerpt</legend>
      <SelectField
        options={evidence.map((row) => ({
          value: row.label,
          label: `${row.label} · ${row.source_name}`,
        }))}
        label="Evidence record"
        value={label}
        onChange={(event) => {
          setLabel(event.target.value);
          setSelection(null);
        }}
      ></SelectField>
      <SelectField
        options={[
          { value: 'title', label: 'Title' },
          { value: 'summary', label: 'Captured summary' },
        ]}
        label="Original field"
        value={field}
        onChange={(event) => {
          setField(event.target.value === 'summary' ? 'summary' : 'title');
          setSelection(null);
        }}
      ></SelectField>
      <TextAreaField
        label="Select the exact excerpt"
        hint="Select text here using the mouse or Shift and arrow keys, then add it. Up to 1,200 characters."
        readOnly
        rows={5}
        value={text.replace(/\r\n?/g, '\n')}
        onSelect={(event) => {
          const input = event.currentTarget;
          setSelection(selectedTextareaExcerpt(text, input.selectionStart, input.selectionEnd));
        }}
      />
      <SelectField
        options={[
          { value: 'supporting', label: 'Supporting' },
          { value: 'opposing', label: 'Opposing' },
          { value: 'context', label: 'Context' },
        ]}
        label="Evidence relationship"
        value={relation}
        onChange={(event) => setRelation(event.target.value as Citation['relation'])}
      ></SelectField>
      <Button
        type="button"
        variant="secondary"
        disabled={!selection || !item}
        onClick={() => {
          if (selection && item) onAdd({ label, field, relation, ...selection });
        }}
      >
        Add selected excerpt
      </Button>
    </fieldset>
  );
}

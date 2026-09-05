import { useState } from 'react';
import type { SyntheticEvent } from 'react';

import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SelectField, TextAreaField, TextField } from '@/components/ui/Field';
import type { Country } from '@/lib/api/geoSchemas';
import type { ReportRequest, ReportTemplate } from '@/lib/api/reports';

export interface GenerateFormProps {
  templates: readonly ReportTemplate[];
  countries: readonly Country[];
  busy: boolean;
  error: string | null;
  onSubmit: (request: ReportRequest) => void;
}

/** Choose a product, a scope and (for Ask the Eye) a question. */
export function GenerateForm({ templates, countries, busy, error, onSubmit }: GenerateFormProps) {
  const [templateId, setTemplateId] = useState(templates[0]?.id ?? 'intsum');
  const [country, setCountry] = useState('');
  const [question, setQuestion] = useState('');
  const [windowHours, setWindowHours] = useState('');
  const [advocacy, setAdvocacy] = useState(false);
  const template = templates.find((item) => item.id === templateId) ?? templates[0];

  const submit = (event: SyntheticEvent<HTMLFormElement>) => {
    event.preventDefault();
    const request: ReportRequest = { template: templateId };
    if (country !== '') request.country = country;
    if (question.trim() !== '') request.question = question.trim();
    if (windowHours.trim() !== '') request.window_hours = Number(windowHours);
    if (advocacy) request.devils_advocacy = true;
    onSubmit(request);
  };

  return (
    <form
      onSubmit={submit}
      aria-label="Generate a report"
      className="flex flex-col gap-4 rounded-card border border-line bg-surface p-4"
    >
      <div className="grid gap-4 md:grid-cols-3">
        <SelectField
          label="Product"
          value={templateId}
          onChange={(event) => {
            setTemplateId(event.target.value);
          }}
          options={templates.map((item) => ({ value: item.id, label: item.title }))}
        />
        <SelectField
          label="Nation"
          hint={template?.needs_country ? 'Required for this product.' : 'Optional scope.'}
          value={country}
          onChange={(event) => {
            setCountry(event.target.value);
          }}
          options={[
            { value: '', label: 'Whole world' },
            ...countries.map((item) => ({ value: item.iso2, label: item.name })),
          ]}
        />
        <TextField
          label="Window (hours)"
          type="number"
          min={1}
          max={336}
          placeholder={template ? String(template.window_hours) : ''}
          value={windowHours}
          onChange={(event) => {
            setWindowHours(event.target.value);
          }}
        />
      </div>
      {template?.needs_question && (
        <TextAreaField
          label="Question"
          hint="What do you want the Eye to assess from the live evidence?"
          value={question}
          onChange={(event) => {
            setQuestion(event.target.value);
          }}
          required
          maxLength={1000}
        />
      )}
      <label className="flex items-center gap-2 text-sm text-text">
        <input
          type="checkbox"
          checked={advocacy}
          onChange={(event) => {
            setAdvocacy(event.target.checked);
          }}
          className="accent-ember"
        />
        Devil&apos;s advocacy: a second model call attacks the top judgement and can lower its
        confidence
      </label>
      {template && <p className="text-sm text-muted">{template.purpose}</p>}
      {error === null ? null : <Alert tone="error">{error}</Alert>}
      <div>
        <Button type="submit" busy={busy} disabled={templates.length === 0}>
          Generate
        </Button>
      </div>
    </form>
  );
}

import { useState } from 'react';
import type { SyntheticEvent } from 'react';

import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SelectField, TextField } from '@/components/ui/Field';
import type { ReportTemplate } from '@/lib/api/reports';
import type { IndicatorRequest } from '@/lib/api/warning';
import { parseCategories, parseCommaList, parseCountries } from '@/lib/text';

export const WINDOWS = [
  { value: '60', label: '1 hour' },
  { value: '360', label: '6 hours' },
  { value: '1440', label: '1 day' },
  { value: '10080', label: '7 days' },
];

export function describeWindow(minutes: number): string {
  if (minutes % 1440 === 0) return `${String(minutes / 1440)} d`;
  if (minutes % 60 === 0) return `${String(minutes / 60)} h`;
  return `${String(minutes)} min`;
}

interface IndicatorFormProps {
  templates: readonly ReportTemplate[];
  busy: boolean;
  error: string | null;
  onSubmit: (request: IndicatorRequest) => void;
}

/** A standing rule: what to watch, how many in what window, and what to do when it fires. */
export function IndicatorForm({ templates, busy, error, onSubmit }: IndicatorFormProps) {
  const [name, setName] = useState('');
  const [countries, setCountries] = useState('');
  const [keywords, setKeywords] = useState('');
  const [categories, setCategories] = useState('');
  const [threshold, setThreshold] = useState('1');
  const [window, setWindow] = useState('360');
  const [template, setTemplate] = useState('');

  const submit = (event: SyntheticEvent<HTMLFormElement>) => {
    event.preventDefault();
    onSubmit({
      name: name.trim(),
      countries: parseCountries(countries),
      keywords: parseCommaList(keywords),
      categories: parseCategories(categories),
      threshold: Math.max(1, Number(threshold) || 1),
      window_minutes: Number(window),
      report_template: template === '' ? null : template,
    });
  };

  return (
    <form
      onSubmit={submit}
      aria-label="New indicator"
      className="flex flex-col gap-3 rounded-card border border-line bg-surface p-4"
    >
      <div className="grid gap-3 md:grid-cols-3">
        <TextField
          label="Indicator name"
          value={name}
          onChange={(event) => {
            setName(event.target.value);
          }}
          required
          maxLength={120}
        />
        <TextField
          label="Nations"
          hint="ISO codes, comma separated; blank watches everywhere."
          value={countries}
          onChange={(event) => {
            setCountries(event.target.value);
          }}
        />
        <TextField
          label="Categories"
          hint="Comma separated, for example conflict, news."
          value={categories}
          onChange={(event) => {
            setCategories(event.target.value);
          }}
        />
        <TextField
          label="Keywords"
          hint="Any of these in a title or summary, comma separated."
          value={keywords}
          onChange={(event) => {
            setKeywords(event.target.value);
          }}
        />
        <TextField
          label="Threshold"
          hint="Fires at this many matching items in the window."
          type="number"
          min={1}
          max={10000}
          value={threshold}
          onChange={(event) => {
            setThreshold(event.target.value);
          }}
        />
        <SelectField
          label="Window"
          value={window}
          onChange={(event) => {
            setWindow(event.target.value);
          }}
          options={WINDOWS}
        />
        <SelectField
          label="Report when it fires"
          hint="Generated as you, scoped like the indicator."
          value={template}
          onChange={(event) => {
            setTemplate(event.target.value);
          }}
          options={[
            { value: '', label: 'No report' },
            ...templates.map((item) => ({ value: item.id, label: item.title })),
          ]}
        />
      </div>
      {error === null ? null : <Alert tone="error">{error}</Alert>}
      <div>
        <Button type="submit" busy={busy}>
          Add indicator
        </Button>
      </div>
    </form>
  );
}

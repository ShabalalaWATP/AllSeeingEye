import { useState } from 'react';
import type { SyntheticEvent } from 'react';

import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SelectField, TextField } from '@/components/ui/Field';
import type { Country } from '@/lib/api/geoSchemas';
import type { ReportTemplate } from '@/lib/api/reports';
import type { Schedule, ScheduleRequest } from '@/lib/api/schedules';

const CADENCES = [
  { value: 'daily', label: 'Every day' },
  { value: 'weekdays', label: 'Weekdays' },
  { value: 'weekly', label: 'Once a week' },
];
const WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
const HOURS = Array.from({ length: 24 }, (_, hour) => ({
  value: String(hour),
  label: `${String(hour).padStart(2, '0')}:00 UTC`,
}));

export function describeCadence(schedule: Schedule): string {
  const at = `${String(schedule.hour_utc).padStart(2, '0')}:00 UTC`;
  if (schedule.cadence === 'weekly') return `${WEEKDAYS[schedule.weekday] ?? ''} at ${at}`;
  if (schedule.cadence === 'weekdays') return `weekdays at ${at}`;
  return `daily at ${at}`;
}

interface ScheduleFormProps {
  templates: readonly ReportTemplate[];
  countries: readonly Country[];
  busy: boolean;
  error: string | null;
  onSubmit: (request: ScheduleRequest) => void;
}

/** A standing order: which product, for which nation, at which UTC hour, how often. */
export function ScheduleForm({ templates, countries, busy, error, onSubmit }: ScheduleFormProps) {
  const [name, setName] = useState('');
  const [template, setTemplate] = useState('intsum');
  const [country, setCountry] = useState('');
  const [hour, setHour] = useState('6');
  const [cadence, setCadence] = useState<'daily' | 'weekdays' | 'weekly'>('daily');
  const [weekday, setWeekday] = useState('0');
  const submit = (event: SyntheticEvent<HTMLFormElement>) => {
    event.preventDefault();
    onSubmit({
      name: name.trim(),
      template_id: template,
      country_iso: country === '' ? null : country,
      hour_utc: Number(hour),
      cadence,
      weekday: Number(weekday),
    });
  };
  return (
    <form
      onSubmit={submit}
      aria-label="New schedule"
      className="flex flex-col gap-3 rounded-card border border-line bg-surface p-4"
    >
      <div className="grid gap-3 md:grid-cols-3">
        <TextField
          label="Schedule name"
          value={name}
          onChange={(event) => {
            setName(event.target.value);
          }}
          required
          maxLength={120}
        />
        <SelectField
          label="Product"
          value={template}
          onChange={(event) => {
            setTemplate(event.target.value);
          }}
          options={templates
            .filter((item) => !item.needs_conflict && !item.needs_hazard && !item.needs_question)
            .map((item) => ({ value: item.id, label: item.title }))}
        />
        <SelectField
          label="Nation"
          value={country}
          onChange={(event) => {
            setCountry(event.target.value);
          }}
          options={[
            { value: '', label: 'Whole world' },
            ...countries.map((item) => ({ value: item.iso2, label: item.name })),
          ]}
        />
        <SelectField
          label="Hour"
          value={hour}
          onChange={(event) => {
            setHour(event.target.value);
          }}
          options={HOURS}
        />
        <SelectField
          label="Cadence"
          value={cadence}
          onChange={(event) => {
            const value = event.target.value;
            setCadence(value === 'weekdays' || value === 'weekly' ? value : 'daily');
          }}
          options={CADENCES}
        />
        {cadence === 'weekly' && (
          <SelectField
            label="Weekday"
            value={weekday}
            onChange={(event) => {
              setWeekday(event.target.value);
            }}
            options={WEEKDAYS.map((label, index) => ({ value: String(index), label }))}
          />
        )}
      </div>
      {error === null ? null : <Alert tone="error">{error}</Alert>}
      <div>
        <Button type="submit" busy={busy}>
          Add schedule
        </Button>
      </div>
    </form>
  );
}

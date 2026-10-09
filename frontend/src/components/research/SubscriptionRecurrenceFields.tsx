import { SelectField, TextField } from '@/components/ui/Field';
import type { FieldErrorState } from '@/lib/api/fieldErrors';

export type BriefCadence =
  'daily' | 'weekdays' | 'weekly' | 'monthly' | 'quarterly' | 'semiannual' | 'annual';
export const RECURRENCE_FIELDS = {
  cadence: 'Cadence',
  timezone: 'IANA timezone',
  time: { label: 'Local time', paths: ['local_hour', 'local_minute'] },
  weekday: 'Weekday',
  monthday: 'Day of month',
  anchor_month: 'Starting month',
} as const;
export interface RecurrenceDraft {
  cadence: BriefCadence;
  timezone: string;
  time: string;
  weekday: string;
  monthday: string;
  anchorMonth: string;
}
const cadences = [
  ['daily', 'Daily'],
  ['weekdays', 'Weekdays'],
  ['weekly', 'Weekly'],
  ['monthly', 'Monthly'],
  ['quarterly', 'Every 3 months'],
  ['semiannual', 'Every 6 months'],
  ['annual', 'Annual'],
] as const;
const weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
const months = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
];

export function SubscriptionRecurrenceFields({
  value,
  change,
  errors,
}: {
  value: RecurrenceDraft;
  change: (patch: Partial<RecurrenceDraft>) => void;
  errors: Pick<FieldErrorState<keyof typeof RECURRENCE_FIELDS>, 'field'>;
}) {
  return (
    <>
      <div className="grid gap-3 sm:grid-cols-3">
        <SelectField
          label="Cadence"
          {...errors.field('cadence')}
          value={value.cadence}
          onChange={(event) => change({ cadence: event.target.value as BriefCadence })}
          options={cadences.map(([value, label]) => ({ value, label }))}
        />
        <TextField
          label="IANA timezone"
          {...errors.field('timezone')}
          required
          maxLength={100}
          value={value.timezone}
          onChange={(event) => change({ timezone: event.target.value })}
        />
        <TextField
          label="Local time"
          {...errors.field('time')}
          type="time"
          step={60}
          required
          value={value.time}
          onChange={(event) => change({ time: event.target.value })}
        />
      </div>
      {value.cadence === 'weekly' && (
        <SelectField
          label="Weekday"
          {...errors.field('weekday')}
          value={value.weekday}
          onChange={(event) => change({ weekday: event.target.value })}
          options={weekdays.map((label, index) => ({ value: String(index), label }))}
        />
      )}
      {['monthly', 'quarterly', 'semiannual', 'annual'].includes(value.cadence) && (
        <TextField
          label="Day of month"
          {...errors.field('monthday')}
          type="number"
          min={1}
          max={31}
          required
          value={value.monthday}
          onChange={(event) => change({ monthday: event.target.value })}
          hint="Short months use their last day. Later months keep your chosen day."
        />
      )}
      {['quarterly', 'semiannual', 'annual'].includes(value.cadence) && (
        <SelectField
          label="Starting month"
          {...errors.field('anchor_month')}
          value={value.anchorMonth}
          onChange={(event) => change({ anchorMonth: event.target.value })}
          options={months.map((label, index) => ({ value: String(index + 1), label }))}
        />
      )}
    </>
  );
}

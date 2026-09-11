import { SelectField, TextField } from '@/components/ui/Field';
import type { Schedule } from '@/lib/api/schedules';

export type Cadence = 'daily' | 'weekdays' | 'weekly' | 'monthly';
const WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
const HOURS = Array.from({ length: 24 }, (_, hour) => ({
  value: String(hour),
  label: `${String(hour).padStart(2, '0')}:00 UTC`,
}));

export function describeCadence(schedule: Schedule): string {
  const at = `${String(schedule.hour_utc).padStart(2, '0')}:00 UTC`;
  if (schedule.cadence === 'monthly') return `day ${schedule.monthday} each month at ${at}`;
  if (schedule.cadence === 'weekly') return `${WEEKDAYS[schedule.weekday] ?? ''} at ${at}`;
  if (schedule.cadence === 'weekdays') return `weekdays at ${at}`;
  return `daily at ${at}`;
}

export function ScheduleTiming({
  cadence,
  hour,
  weekday,
  monthday,
  lookback,
  onCadence,
  onHour,
  onWeekday,
  onMonthday,
  onLookback,
}: {
  cadence: Cadence;
  hour: string;
  weekday: string;
  monthday: string;
  lookback: string;
  onCadence: (value: Cadence) => void;
  onHour: (value: string) => void;
  onWeekday: (value: string) => void;
  onMonthday: (value: string) => void;
  onLookback: (value: string) => void;
}) {
  return (
    <fieldset className="space-y-3 border-t border-line pt-5">
      <legend className="text-sm font-semibold">When to research</legend>
      <div className="grid gap-3 sm:grid-cols-2">
        <SelectField
          label="Cadence"
          value={cadence}
          onChange={(event) => onCadence(event.target.value as Cadence)}
          options={[
            { value: 'weekly', label: 'Every week' },
            { value: 'monthly', label: 'Every month' },
            { value: 'daily', label: 'Every day' },
            { value: 'weekdays', label: 'Weekdays' },
          ]}
        />
        <SelectField
          label="Hour"
          value={hour}
          onChange={(event) => onHour(event.target.value)}
          options={HOURS}
        />
        {cadence === 'weekly' && (
          <SelectField
            label="Weekday"
            value={weekday}
            onChange={(event) => onWeekday(event.target.value)}
            options={WEEKDAYS.map((label, index) => ({ value: String(index), label }))}
          />
        )}
        {cadence === 'monthly' && (
          <TextField
            label="Day of month"
            type="number"
            min={1}
            max={31}
            required
            value={monthday}
            onChange={(event) => onMonthday(event.target.value)}
            hint="For short months, runs on the last day. Later months keep your chosen day."
          />
        )}
        <TextField
          label="Look back, days"
          type="number"
          min={1}
          max={730}
          required
          value={lookback}
          onChange={(event) => onLookback(event.target.value)}
          hint="Search the preceding 1 to 730 days at each run, within each source's available history."
        />
      </div>
      <p className="text-xs text-muted">
        Times use UTC all year. The server must be running. Each completed run saves a report.
      </p>
    </fieldset>
  );
}

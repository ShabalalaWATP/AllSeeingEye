import { SelectField, TextField } from '@/components/ui/Field';
import type { Schedule } from '@/lib/api/schedules';

export type LookbackUnit = 'days' | 'hours' | 'default';
export type Cadence =
  'daily' | 'weekdays' | 'weekly' | 'monthly' | 'quarterly' | 'semiannual' | 'annual';
const MONTHS = [
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
export const calendarCadence = (cadence: Cadence) =>
  ['monthly', 'quarterly', 'semiannual', 'annual'].includes(cadence);
const WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
const HOURS = Array.from({ length: 24 }, (_, hour) => ({
  value: String(hour),
  label: `${String(hour).padStart(2, '0')}:00 UTC`,
}));

export function describeCadence(schedule: Schedule): string {
  const at =
    schedule.local_hour === undefined || !schedule.timezone
      ? `${String(schedule.hour_utc).padStart(2, '0')}:00 UTC`
      : `${String(schedule.local_hour).padStart(2, '0')}:${String(schedule.local_minute ?? 0).padStart(2, '0')} ${schedule.timezone}`;
  if (schedule.cadence === 'monthly') return `day ${schedule.monthday} each month at ${at}`;
  if (['quarterly', 'semiannual', 'annual'].includes(schedule.cadence)) {
    const period =
      schedule.cadence === 'quarterly'
        ? '3 months'
        : schedule.cadence === 'semiannual'
          ? '6 months'
          : 'year';
    return `day ${schedule.monthday} every ${period}, from ${MONTHS[schedule.anchor_month - 1]} at ${at}`;
  }
  if (schedule.cadence === 'weekly') return `${WEEKDAYS[schedule.weekday] ?? ''} at ${at}`;
  if (schedule.cadence === 'weekdays') return `weekdays at ${at}`;
  return `daily at ${at}`;
}

export function ScheduleTiming({
  cadence,
  hour,
  weekday,
  monthday,
  anchorMonth,
  onAnchorMonth,
  lookback,
  lookbackUnit,
  onLookbackUnit,
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
  anchorMonth: string;
  onAnchorMonth: (value: string) => void;
  lookback: string;
  lookbackUnit: LookbackUnit;
  onLookbackUnit: (value: LookbackUnit) => void;
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
            { value: 'daily', label: 'Daily' },
            { value: 'weekly', label: 'Weekly' },
            { value: 'monthly', label: 'Monthly' },
            { value: 'quarterly', label: '3 monthly' },
            { value: 'semiannual', label: '6 monthly' },
            { value: 'annual', label: 'Annual' },
            ...(cadence === 'weekdays'
              ? [{ value: 'weekdays', label: 'Weekdays (existing)' }]
              : []),
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
        {calendarCadence(cadence) && (
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
        {['quarterly', 'semiannual', 'annual'].includes(cadence) && (
          <SelectField
            label="Starting month"
            value={anchorMonth}
            onChange={(event) => onAnchorMonth(event.target.value)}
            options={MONTHS.map((label, index) => ({ value: String(index + 1), label }))}
            hint="The first upcoming matching date is used. The next run shows the exact date."
          />
        )}
        <SelectField
          label="Search period"
          value={lookbackUnit}
          onChange={(event) => onLookbackUnit(event.target.value as LookbackUnit)}
          options={[
            { value: 'days', label: 'Number of days' },
            { value: 'hours', label: 'Number of hours' },
            { value: 'default', label: 'Match update frequency' },
          ]}
        />
        {lookbackUnit !== 'default' ? (
          <TextField
            label={lookbackUnit === 'hours' ? 'Look back, hours' : 'Look back, days'}
            type="number"
            min={1}
            max={lookbackUnit === 'hours' ? 17520 : 730}
            required
            value={lookback}
            onChange={(event) => onLookback(event.target.value)}
            hint="Search this period before each run, within each source's available history. Maximum two years."
          />
        ) : (
          <p className="text-xs text-muted">
            Uses a search period matching the update frequency, within each source's available
            history.
          </p>
        )}
      </div>
      <p className="text-xs text-muted">
        Times use UTC all year. The server must be running. Updates are saved in the app, not
        emailed.
      </p>
    </fieldset>
  );
}

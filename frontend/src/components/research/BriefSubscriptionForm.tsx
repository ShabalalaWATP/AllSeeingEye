import { useState, type SyntheticEvent } from 'react';

import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SelectField, TextField } from '@/components/ui/Field';
import type { BriefSubscriptionSettings } from '@/lib/api/briefSubscriptions';
import type { ResearchBrief } from '@/lib/api/researchBriefSchema';

export type BriefCadence =
  'daily' | 'weekdays' | 'weekly' | 'monthly' | 'quarterly' | 'semiannual' | 'annual';
const cadenceOptions = [
  { value: 'daily', label: 'Daily' },
  { value: 'weekdays', label: 'Weekdays' },
  { value: 'weekly', label: 'Weekly' },
  { value: 'monthly', label: 'Monthly' },
  { value: 'quarterly', label: 'Every 3 months' },
  { value: 'semiannual', label: 'Every 6 months' },
  { value: 'annual', label: 'Annual' },
];
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
const calendar = (cadence: BriefCadence) =>
  ['monthly', 'quarterly', 'semiannual', 'annual'].includes(cadence);

export function BriefSubscriptionForm({
  brief,
  busy,
  error,
  onCreate,
  onCancel,
  initialSettings,
  duplicate = false,
}: {
  brief: ResearchBrief;
  busy: boolean;
  error: string | null;
  onCreate: (settings: BriefSubscriptionSettings) => void;
  onCancel: () => void;
  initialSettings?: BriefSubscriptionSettings;
  duplicate?: boolean;
}) {
  const [name, setName] = useState(initialSettings?.name ?? brief.identity.title);
  const [timezone, setTimezone] = useState(
    initialSettings?.timezone ?? Intl.DateTimeFormat().resolvedOptions().timeZone,
  );
  const [hour, setHour] = useState(String(initialSettings?.local_hour ?? 6).padStart(2, '0'));
  const [minute, setMinute] = useState(String(initialSettings?.local_minute ?? 0).padStart(2, '0'));
  const [cadence, setCadence] = useState<BriefCadence>(initialSettings?.cadence ?? 'daily');
  const [weekday, setWeekday] = useState(String(initialSettings?.weekday ?? 0));
  const [monthday, setMonthday] = useState(String(initialSettings?.monthday ?? 1));
  const [anchorMonth, setAnchorMonth] = useState(String(initialSettings?.anchor_month ?? 1));
  const [policy, setPolicy] = useState<BriefSubscriptionSettings['collection_policy']>(
    initialSettings?.collection_policy ?? 'rolling_snapshot',
  );
  const [notify, setNotify] = useState(initialSettings?.notify_on_change ?? false);
  const [avoid, setAvoid] = useState(initialSettings?.avoid_repetition ?? true);
  const [issue, setIssue] = useState<string | null>(null);
  const submit = (event: SyntheticEvent<HTMLFormElement, SubmitEvent>) => {
    event.preventDefault();
    if (busy) return;
    const local_hour = Number(hour);
    const local_minute = Number(minute);
    const day = Number(monthday);
    let validZone = true;
    try {
      new Intl.DateTimeFormat('en-GB', { timeZone: timezone });
    } catch {
      validZone = false;
    }
    const problem =
      !name.trim() || name.length > 120
        ? 'Enter a name of at most 120 characters.'
        : !validZone || timezone.length > 100
          ? 'Choose a valid IANA timezone.'
          : !Number.isInteger(local_hour) ||
              local_hour < 0 ||
              local_hour > 23 ||
              !Number.isInteger(local_minute) ||
              local_minute < 0 ||
              local_minute > 59
            ? 'Choose a valid local time.'
            : !Number.isInteger(day) || day < 1 || day > 31
              ? 'Choose a day from 1 to 31.'
              : null;
    setIssue(problem);
    if (problem) return;
    onCreate({
      name: name.trim(),
      timezone,
      local_hour,
      local_minute,
      cadence,
      weekday: Number(weekday),
      monthday: day,
      anchor_month: Number(anchorMonth),
      collection_policy: policy,
      enabled: duplicate ? false : (initialSettings?.enabled ?? true),
      notify_on_change: notify,
      avoid_repetition: avoid,
    });
  };
  return (
    <form
      aria-label={
        duplicate ? 'Duplicate Research Brief subscription' : 'Subscribe to Research Brief'
      }
      onSubmit={submit}
      className="space-y-4 rounded-lg border border-line bg-ground/50 p-4"
      noValidate
    >
      <div>
        <h3 className="font-semibold">
          {duplicate ? 'Create a paused copy' : 'Subscribe to this brief'}
        </h3>
        <p className="text-xs text-muted">
          Revision {brief.identity.revision} · {brief.output.depth} · {brief.output.language} ·{' '}
          {brief.question.requirements.length} requirements. Scope, sources and output stay pinned
          to this revision.
        </p>
        {duplicate && (
          <p className="mt-2 text-xs text-muted">This copy remains paused until you resume it.</p>
        )}
      </div>
      <TextField
        label="Subscription name"
        maxLength={120}
        required
        value={name}
        onChange={(event) => setName(event.target.value)}
      />
      <div className="grid gap-3 sm:grid-cols-3">
        <SelectField
          label="Cadence"
          value={cadence}
          onChange={(event) => setCadence(event.target.value as BriefCadence)}
          options={cadenceOptions}
        />
        <TextField
          label="IANA timezone"
          value={timezone}
          required
          maxLength={100}
          onChange={(event) => setTimezone(event.target.value)}
        />
        <TextField
          label="Local time"
          type="time"
          step={60}
          required
          value={`${hour}:${minute}`}
          onChange={(event) => {
            const [nextHour = '06', nextMinute = '00'] = event.target.value.split(':');
            setHour(nextHour);
            setMinute(nextMinute);
          }}
        />
      </div>
      {cadence === 'weekly' && (
        <SelectField
          label="Weekday"
          value={weekday}
          onChange={(event) => setWeekday(event.target.value)}
          options={weekdays.map((label, index) => ({ value: String(index), label }))}
        />
      )}
      {calendar(cadence) && (
        <TextField
          label="Day of month"
          type="number"
          min={1}
          max={31}
          value={monthday}
          onChange={(event) => setMonthday(event.target.value)}
        />
      )}
      {['quarterly', 'semiannual', 'annual'].includes(cadence) && (
        <SelectField
          label="Starting month"
          value={anchorMonth}
          onChange={(event) => setAnchorMonth(event.target.value)}
          options={months.map((label, index) => ({ value: String(index + 1), label }))}
        />
      )}
      <SelectField
        label="Future collection window"
        value={policy}
        onChange={(event) => setPolicy(event.target.value as typeof policy)}
        options={[
          { value: 'rolling_snapshot', label: 'Use the brief’s rolling window' },
          { value: 'since_last_success', label: 'Since the last successful update' },
        ]}
      />
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={notify}
          onChange={(event) => setNotify(event.target.checked)}
        />
        Notify in app when evidence changes
      </label>
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={avoid}
          onChange={(event) => setAvoid(event.target.checked)}
        />
        Avoid repeating unchanged evidence
      </label>
      {issue && <Alert tone="error">{issue}</Alert>}
      {error && <Alert tone="error">{error}</Alert>}
      <div className="flex gap-2">
        <Button type="submit" busy={busy}>
          {duplicate ? 'Create paused copy' : 'Create subscription'}
        </Button>
        <Button variant="ghost" onClick={onCancel} disabled={busy}>
          Cancel
        </Button>
      </div>
    </form>
  );
}

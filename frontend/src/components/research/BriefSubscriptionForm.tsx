import { useState, type SyntheticEvent } from 'react';

import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SelectField, TextField } from '@/components/ui/Field';
import { FormErrors } from '@/components/ui/FormErrors';
import { useFieldErrors } from '@/lib/api/fieldErrors';
import type { BriefSubscriptionSettings } from '@/lib/api/briefSubscriptions';
import type { ResearchBrief } from '@/lib/api/researchBriefSchema';

import { SubscriptionRecurrenceFields } from './SubscriptionRecurrenceFields';
import type { BriefCadence } from './SubscriptionRecurrenceFields';
export type { BriefCadence } from './SubscriptionRecurrenceFields';

/** Form fields for the API paths a brief subscription request can reject. */
const SUBSCRIPTION_FIELDS = {
  name: 'Subscription name',
  cadence: 'Cadence',
  timezone: 'IANA timezone',
  time: { label: 'Local time', paths: ['local_hour', 'local_minute'] },
  weekday: 'Weekday',
  monthday: 'Day of month',
  anchor_month: 'Starting month',
  collection_policy: 'Future collection window',
} as const;

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
  /** A safe message, or the failed save to map to field reasons. */
  error: unknown;
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
  const errors = useFieldErrors(error, SUBSCRIPTION_FIELDS);
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
          : !/^\d{2}:\d{2}$/.test(`${hour}:${minute}`) ||
              !Number.isInteger(local_hour) ||
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
        {...errors.field('name')}
        maxLength={120}
        required
        value={name}
        onChange={(event) => setName(event.target.value)}
      />
      <SubscriptionRecurrenceFields
        value={{ cadence, timezone, time: `${hour}:${minute}`, weekday, monthday, anchorMonth }}
        change={(patch) => {
          if (patch.cadence !== undefined) setCadence(patch.cadence);
          if (patch.timezone !== undefined) setTimezone(patch.timezone);
          if (patch.time !== undefined) {
            const [nextHour = '', nextMinute = ''] = patch.time.split(':');
            setHour(nextHour);
            setMinute(nextMinute);
          }
          if (patch.weekday !== undefined) setWeekday(patch.weekday);
          if (patch.monthday !== undefined) setMonthday(patch.monthday);
          if (patch.anchorMonth !== undefined) setAnchorMonth(patch.anchorMonth);
        }}
        errors={errors}
      />
      <SelectField
        label="Future collection window"
        {...errors.field('collection_policy')}
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
      <FormErrors errors={errors} />
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

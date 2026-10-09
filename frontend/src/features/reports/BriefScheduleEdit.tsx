import { useEffect, useRef, useState, type SyntheticEvent } from 'react';

import {
  RECURRENCE_FIELDS,
  SubscriptionRecurrenceFields,
} from '@/components/research/SubscriptionRecurrenceFields';
import type { RecurrenceDraft } from '@/components/research/SubscriptionRecurrenceFields';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { TextField } from '@/components/ui/Field';
import { FormErrors } from '@/components/ui/FormErrors';
import {
  briefSubscriptionSettingsSchema,
  updateBriefSubscriptionSettings,
} from '@/lib/api/briefSubscriptions';
import { useFieldErrors } from '@/lib/api/fieldErrors';
import type { Schedule } from '@/lib/api/schedules';

const FIELDS = { name: 'Subscription name', ...RECURRENCE_FIELDS } as const;
const recurrenceSchema = briefSubscriptionSettingsSchema.pick({
  cadence: true,
  timezone: true,
  local_hour: true,
  local_minute: true,
  weekday: true,
  monthday: true,
  anchor_month: true,
  name: true,
});

export function BriefScheduleEdit({
  source,
  onCancel,
  onSaved,
}: {
  source: Schedule;
  onCancel: () => void;
  onSaved: () => void;
}) {
  const [name, setName] = useState(source.name);
  const [draft, setDraft] = useState<RecurrenceDraft>({
    cadence: source.cadence as RecurrenceDraft['cadence'],
    timezone: source.timezone ?? 'UTC',
    time: `${String(source.local_hour ?? source.hour_utc).padStart(2, '0')}:${String(source.local_minute ?? 0).padStart(2, '0')}`,
    weekday: String(source.weekday),
    monthday: String(source.monthday),
    anchorMonth: String(source.anchor_month),
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [issue, setIssue] = useState<string | null>(null);
  const controller = useRef<AbortController | null>(null);
  const form = useRef<HTMLFormElement>(null);
  // Keep the revision seen when editing began, even when the list refreshes underneath.
  const [original] = useState(source);
  const errors = useFieldErrors(error, FIELDS);
  useEffect(() => {
    form.current?.querySelector('input')?.focus();
    return () => controller.current?.abort();
  }, []);
  const submit = async (event: SyntheticEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (busy || !original.settings_revision) return;
    const [hour, minute] = draft.time.split(':');
    const parsed = recurrenceSchema.safeParse({
      name: name.trim(),
      timezone: draft.timezone,
      cadence: draft.cadence,
      local_hour: Number(hour),
      local_minute: Number(minute),
      weekday: Number(draft.weekday),
      monthday: Number(draft.monthday),
      anchor_month: Number(draft.anchorMonth),
    });
    let validZone = true;
    try {
      new Intl.DateTimeFormat('en-GB', { timeZone: draft.timezone });
    } catch {
      validZone = false;
    }
    if (!parsed.success || !validZone || !/^\d{2}:\d{2}$/.test(draft.time)) {
      setIssue(
        !name.trim()
          ? 'Enter a subscription name.'
          : 'Check the timezone, local time and recurrence fields.',
      );
      form.current?.querySelector('input')?.focus();
      return;
    }
    setIssue(null);
    setError(null);
    setBusy(true);
    const request = new AbortController();
    controller.current = request;
    try {
      await updateBriefSubscriptionSettings(
        original.id,
        {
          ...parsed.data,
          expected_revision: original.settings_revision,
        },
        request.signal,
      );
      if (!request.signal.aborted) onSaved();
    } catch (caught) {
      if (!request.signal.aborted) setError(caught);
    } finally {
      if (!request.signal.aborted) setBusy(false);
    }
  };
  return (
    <form
      ref={form}
      aria-label="Edit Research Brief subscription"
      onSubmit={(event) => void submit(event)}
      noValidate
      className="max-w-2xl space-y-4 rounded-lg border border-line bg-ground/50 p-4"
    >
      <h3 className="font-semibold">Edit subscription settings</h3>
      <p className="text-sm text-muted">
        Research Brief revision {source.brief_revision} and edition history stay pinned. Only the
        name and recurrence change.
      </p>
      <p className="text-xs text-muted">
        {source.enabled
          ? 'This subscription stays active.'
          : 'This subscription remains paused until you resume it.'}
      </p>
      {!original.settings_revision && (
        <Alert tone="error">Reload subscriptions before editing these settings.</Alert>
      )}
      <fieldset disabled={busy || !original.settings_revision} className="space-y-4">
        <TextField
          label="Subscription name"
          {...errors.field('name')}
          required
          maxLength={120}
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
        <SubscriptionRecurrenceFields
          value={draft}
          change={(patch) => setDraft((value) => ({ ...value, ...patch }))}
          errors={errors}
        />
      </fieldset>
      <p className="text-xs text-muted">
        Times follow the selected timezone. Missing daylight-saving times use the next valid minute;
        repeated times run once. Changing recurrence recalculates the next run.
      </p>
      {issue && <Alert tone="error">{issue}</Alert>}
      <FormErrors errors={errors} />
      <div className="flex gap-2">
        <Button
          type="submit"
          busy={busy}
          busyLabel="Saving…"
          disabled={!original.settings_revision}
        >
          Save changes
        </Button>
        <Button variant="ghost" onClick={onCancel} disabled={busy}>
          Cancel
        </Button>
      </div>
    </form>
  );
}

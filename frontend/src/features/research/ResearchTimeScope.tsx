import { SelectField, TextField } from '@/components/ui/Field';

export const MAX_RESEARCH_HOURS = 730 * 24;
export interface ResearchDates {
  since: string;
  until: string;
}

export function researchDateError(dates: ResearchDates, now = Date.now()): string | null {
  const start = Date.parse(dates.since),
    end = Date.parse(dates.until);
  if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start)
    return 'Choose a start and end date, with the end after the start.';
  if (end - start > MAX_RESEARCH_HOURS * 3_600_000)
    return 'Choose a search period of no more than two years (730 days).';
  if (end > now) return 'The end of the search period cannot be in the future.';
  return null;
}

export function ResearchTimeScope({
  windowHours,
  setWindowHours,
  dates,
  setDates,
}: {
  windowHours: string;
  setWindowHours: (value: string) => void;
  dates: ResearchDates | null;
  setDates: (value: ResearchDates | null) => void;
}) {
  const utcInput = (value: string) => value.replace(/Z$/, '').slice(0, 16);
  return (
    <fieldset className="space-y-3">
      <legend className="mb-2 text-sm font-medium">Search period</legend>
      <SelectField
        label="Reporting window"
        value={dates ? 'custom' : windowHours}
        className="min-h-11"
        onChange={(event) => {
          if (event.target.value === 'custom') {
            const end = new Date();
            end.setUTCSeconds(0, 0);
            setDates({
              since: new Date(end.getTime() - Number(windowHours) * 3_600_000).toISOString(),
              until: end.toISOString(),
            });
          } else {
            setDates(null);
            setWindowHours(event.target.value);
          }
        }}
        options={[
          { value: '24', label: 'Past 24 hours' },
          { value: '72', label: 'Past 3 days' },
          { value: '168', label: 'Past 7 days' },
          { value: '336', label: 'Past 14 days' },
          { value: '720', label: 'Past 30 days' },
          { value: '2160', label: 'Past 90 days' },
          { value: '8760', label: 'Past year' },
          { value: String(MAX_RESEARCH_HOURS), label: 'Past 2 years' },
          { value: 'custom', label: 'Custom date range' },
        ]}
      />
      {dates && (
        <div className="grid gap-3 sm:grid-cols-2">
          <TextField
            label="Start date (UTC)"
            type="datetime-local"
            value={utcInput(dates.since)}
            max={utcInput(new Date().toISOString())}
            onChange={(event) =>
              setDates({ ...dates, since: event.target.value ? `${event.target.value}:00Z` : '' })
            }
          />
          <TextField
            label="End date (UTC, exclusive)"
            type="datetime-local"
            value={utcInput(dates.until)}
            max={utcInput(new Date().toISOString())}
            onChange={(event) =>
              setDates({ ...dates, until: event.target.value ? `${event.target.value}:00Z` : '' })
            }
          />
        </div>
      )}
      <p className="text-xs leading-relaxed text-muted">
        Search up to two years (730 days). Each source has its own archive limits. Live feeds may
        only cover recent events; preview the collection plan to see source coverage.
      </p>
    </fieldset>
  );
}

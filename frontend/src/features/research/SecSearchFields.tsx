import { TextField } from '@/components/ui/Field';
export interface SecSearchDraft {
  cik: string;
  since: string;
  until: string;
}
export function SecSearchFields({
  value,
  onChange,
  disabled,
}: {
  value: SecSearchDraft;
  onChange: (value: SecSearchDraft) => void;
  disabled: boolean;
}) {
  return (
    <fieldset disabled={disabled} className="grid gap-3 sm:grid-cols-3">
      <legend className="mb-2 text-sm font-medium">Find a company filing</legend>
      <TextField
        label="SEC company identifier (CIK)"
        value={value.cik}
        maxLength={10}
        inputMode="numeric"
        placeholder="For example, 320193"
        hint="Enter 1 to 10 digits, including any leading zeros."
        onChange={(event) => onChange({ ...value, cik: event.target.value })}
      />
      <TextField
        label="Filed from"
        type="date"
        value={value.since}
        onChange={(event) => onChange({ ...value, since: event.target.value })}
      />
      <TextField
        label="Filed through"
        type="date"
        value={value.until}
        onChange={(event) => onChange({ ...value, until: event.target.value })}
      />
    </fieldset>
  );
}

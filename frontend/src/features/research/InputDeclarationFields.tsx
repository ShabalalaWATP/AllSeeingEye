import { SelectField, TextAreaField, TextField } from '@/components/ui/Field';
import type { DeclarationTargets } from '@/lib/api/inputDeclarations';

export interface DeclarationDraft {
  eventId: string;
  field: 'title' | 'summary';
  transform: boolean;
  kind: 'translation' | 'transliteration';
  transformed: string;
  sourceLanguage: string;
  targetLanguage: string;
  sourceScript: string;
  targetScript: string;
  method: string;
  date: boolean;
  rawDate: string;
  calendar: 'gregorian' | 'solar_hijri_icu33' | 'unknown';
  role: 'publication' | 'occurrence' | 'record_validity';
}
export const emptyDeclaration = (): DeclarationDraft => ({
  eventId: '',
  field: 'title',
  transform: false,
  kind: 'transliteration',
  transformed: '',
  sourceLanguage: 'und',
  targetLanguage: 'und',
  sourceScript: '',
  targetScript: '',
  method: '',
  date: false,
  rawDate: '',
  calendar: 'unknown',
  role: 'publication',
});

export function InputDeclarationFields({
  value,
  targets,
  index,
  update,
}: {
  value: DeclarationDraft;
  targets: DeclarationTargets['targets'];
  index: number;
  update: (value: DeclarationDraft) => void;
}) {
  const target = targets.find((row) => row.event_id === value.eventId);
  const original = target?.[value.field] ?? '';
  const prefix = `Declaration ${index + 1}`;
  return (
    <fieldset className="space-y-3 rounded border border-line p-3">
      <legend className="text-sm font-medium">{prefix}</legend>
      <SelectField
        label={`${prefix} passage`}
        value={value.eventId}
        options={[
          { value: '', label: 'Choose an extracted passage' },
          ...targets.map((row) => ({ value: row.event_id, label: row.title })),
        ]}
        onChange={(event) => {
          const selected = targets.find((row) => row.event_id === event.target.value);
          update({
            ...emptyDeclaration(),
            eventId: event.target.value,
            sourceLanguage: selected?.language ?? 'und',
          });
        }}
      />
      <SelectField
        label={`${prefix} original field`}
        value={value.field}
        options={[
          { value: 'title', label: 'Original title' },
          { value: 'summary', label: 'Original source snippet' },
        ]}
        onChange={(event) =>
          update({
            ...value,
            field: event.target.value === 'summary' ? 'summary' : 'title',
            transformed: '',
            rawDate: '',
          })
        }
      />
      <p
        className="max-h-48 overflow-auto whitespace-pre-wrap break-words rounded bg-ground p-3 text-xs"
        dir="auto"
      >
        {original || 'Choose a non-empty original field.'}
      </p>
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={value.transform}
          onChange={(event) => update({ ...value, transform: event.target.checked })}
        />
        {prefix}: supply text transformation
      </label>
      {value.transform && (
        <>
          <SelectField
            label={`${prefix} transformation kind`}
            value={value.kind}
            options={[
              { value: 'transliteration', label: 'Transliteration (script rendering)' },
              { value: 'translation', label: 'Translation (meaning)' },
            ]}
            onChange={(event) =>
              update({
                ...value,
                kind: event.target.value === 'translation' ? 'translation' : 'transliteration',
              })
            }
          />
          <TextAreaField
            label={`${prefix} transformed text`}
            dir="auto"
            value={value.transformed}
            maxLength={2000}
            rows={3}
            hint="Supply the transformation of the whole selected field. Original fields over 2,000 characters cannot be transformed here."
            onChange={(event) => update({ ...value, transformed: event.target.value })}
          />
          <div className="grid gap-3 sm:grid-cols-2">
            <TextField
              label={`${prefix} source language`}
              value={value.sourceLanguage}
              maxLength={16}
              hint="Language code, or und if unknown."
              onChange={(event) => update({ ...value, sourceLanguage: event.target.value })}
            />
            <TextField
              label={`${prefix} target language`}
              value={value.targetLanguage}
              maxLength={16}
              hint="Language code, or und if unknown."
              onChange={(event) => update({ ...value, targetLanguage: event.target.value })}
            />
            <TextField
              label={`${prefix} source script`}
              value={value.sourceScript}
              maxLength={4}
              hint="Optional ISO 15924 code, for example Arab."
              onChange={(event) => update({ ...value, sourceScript: event.target.value })}
            />
            <TextField
              label={`${prefix} target script`}
              value={value.targetScript}
              maxLength={4}
              hint="Optional ISO 15924 code, for example Latn."
              onChange={(event) => update({ ...value, targetScript: event.target.value })}
            />
          </div>
          <TextField
            label={`${prefix} method`}
            value={value.method}
            maxLength={120}
            hint="Name your method or convention. This is your declaration, not a verified model result."
            onChange={(event) => update({ ...value, method: event.target.value })}
          />
        </>
      )}
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={value.date}
          onChange={(event) => update({ ...value, date: event.target.checked })}
        />
        {prefix}: declare a source date
      </label>
      {value.date && (
        <>
          <TextField
            label={`${prefix} raw source date`}
            value={value.rawDate}
            maxLength={300}
            dir="auto"
            hint="Copy exact text from the selected field, including its original digits."
            onChange={(event) => update({ ...value, rawDate: event.target.value })}
          />
          <SelectField
            label={`${prefix} calendar`}
            value={value.calendar}
            options={[
              { value: 'unknown', label: 'Unknown or unsupported calendar' },
              { value: 'gregorian', label: 'Gregorian' },
              { value: 'solar_hijri_icu33', label: 'Solar Hijri, ICU33 arithmetic convention' },
            ]}
            onChange={(event) =>
              update({
                ...value,
                calendar:
                  event.target.value === 'gregorian'
                    ? 'gregorian'
                    : event.target.value === 'solar_hijri_icu33'
                      ? 'solar_hijri_icu33'
                      : 'unknown',
              })
            }
          />
          <SelectField
            label={`${prefix} date role`}
            value={value.role}
            options={[
              { value: 'publication', label: 'Publication date' },
              { value: 'occurrence', label: 'Claimed occurrence date' },
              { value: 'record_validity', label: 'Record validity date' },
            ]}
            onChange={(event) =>
              update({
                ...value,
                role:
                  event.target.value === 'occurrence'
                    ? 'occurrence'
                    : event.target.value === 'record_validity'
                      ? 'record_validity'
                      : 'publication',
              })
            }
          />
          <p className="text-xs text-muted">
            Solar Hijri conversion supports the ICU33 convention, years 1304 to 1468, using
            YYYY-MM-DD. Other Islamic conventions are not supported. No calendar or timezone is
            inferred; ambiguous or invalid dates remain unresolved, and day precision stays a
            calendar day.
          </p>
        </>
      )}
    </fieldset>
  );
}

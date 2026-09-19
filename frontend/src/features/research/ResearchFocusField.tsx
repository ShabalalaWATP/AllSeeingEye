/**
 * What kind of research this is: a general question, or a closer look at one company,
 * domain or private file. Company and domain research also need the name.
 */
import { SelectField, TextField } from '@/components/ui/Field';

import type { ResearchFocus } from './researchRequest';

const FOCUS_OPTIONS = [
  { value: 'general', label: 'General question' },
  { value: 'company', label: 'Company' },
  { value: 'domain', label: 'Domain' },
  { value: 'document', label: 'Private document' },
  { value: 'media', label: 'Private media' },
] as const;

export function ResearchFocusField({
  focus,
  subject,
  onFocus,
  onSubject,
}: {
  focus: ResearchFocus;
  subject: string;
  onFocus: (value: ResearchFocus) => void;
  onSubject: (value: string) => void;
}) {
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <SelectField
        label="Research focus"
        hint="A general question, or a closer look at one company, domain or private file."
        value={focus}
        className="min-h-11"
        options={FOCUS_OPTIONS}
        onChange={(event) => {
          const value = FOCUS_OPTIONS.find((o) => o.value === event.target.value)?.value;
          if (value) onFocus(value);
        }}
      />
      {(focus === 'company' || focus === 'domain') && (
        <TextField
          label={focus === 'company' ? 'Company name' : 'Domain name'}
          className="min-h-11"
          maxLength={300}
          value={subject}
          onChange={(event) => onSubject(event.target.value)}
          hint={
            focus === 'company'
              ? 'Use a full name or explicit registry identifier, such as GB:01234567 for Companies House or LEI: followed by a legal entity identifier.'
              : 'For example, example.org.'
          }
        />
      )}
    </div>
  );
}

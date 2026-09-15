import { useState } from 'react';

import { TextAreaField, TextField } from '@/components/ui/Field';

/** Preserve typed delimiters while storing only normalised canonical list values. */
export function BriefListField({
  label,
  values,
  change,
  multiline = false,
  uppercase = false,
  disabled = false,
  maxLength,
}: {
  label: string;
  values: string[];
  change: (values: string[]) => void;
  multiline?: boolean;
  uppercase?: boolean;
  disabled?: boolean;
  maxLength?: number;
}) {
  const separator = multiline ? '\n' : ',';
  const canonical = JSON.stringify(values);
  const [edit, setEdit] = useState({ canonical, text: values.join(multiline ? '\n' : ', ') });
  const props = {
    label,
    disabled,
    maxLength,
    value: edit.canonical === canonical ? edit.text : values.join(multiline ? '\n' : ', '),
    onChange: (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
      const text = uppercase ? event.target.value.toUpperCase() : event.target.value;
      const next = text
        .split(separator)
        .map((item) => item.trim())
        .filter(Boolean);
      setEdit({ canonical: JSON.stringify(next), text });
      change(next);
    },
  };
  return multiline ? <TextAreaField {...props} /> : <TextField {...props} />;
}

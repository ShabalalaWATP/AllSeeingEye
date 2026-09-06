import { useState } from 'react';
import { Alert } from '@/components/ui/Alert';
import { SelectField, TextField } from '@/components/ui/Field';
import type { Country } from '@/lib/api/geoSchemas';

function recordMode(subject: string) {
  if (subject.startsWith('academic:')) return 'academic';
  if (subject.startsWith('parliament:')) return 'parliament';
  if (subject.startsWith('WB:')) return 'world_bank';
  if (subject.startsWith('ooni:')) return 'ooni';
  return subject ? 'identifier' : 'question';
}

export function GeneralRecordScope({
  subject,
  setSubject,
  country,
  countries,
}: {
  subject: string;
  setSubject: (value: string) => void;
  country: string;
  countries: readonly Country[];
}) {
  const [mode, setMode] = useState(() => recordMode(subject));
  const parts = subject.split(':');
  const targetCountry = parts[1] ?? '';
  const updatePart = (index: number, value: string) => {
    const next = [...parts];
    next[index] = value;
    setSubject(next.join(':'));
  };
  const selectMode = (value: string) => {
    setMode(value);
    const year = new Date().getUTCFullYear();
    const next: Record<string, string> = {
      question: '',
      academic: 'academic:',
      parliament: 'parliament:',
      identifier: '',
      world_bank: `WB:${country || 'GB'}:NY.GDP.MKTP.CD:${year - 5}:${year - 1}`,
      ooni: `ooni:${country || 'IR'}`,
    };
    setSubject(next[value] ?? '');
  };
  const countryOptions = [
    ...(!countries.some((item) => item.iso2 === targetCountry)
      ? [{ value: targetCountry, label: targetCountry || 'Choose a country' }]
      : []),
    ...countries.map((item) => ({ value: item.iso2, label: item.name })),
  ];
  return (
    <fieldset className="space-y-4">
      <legend className="text-sm font-medium">Specialist records</legend>
      <SelectField
        label="Record collection"
        value={mode}
        onChange={(event) => selectMode(event.target.value)}
        options={[
          { value: 'question', label: 'General question' },
          { value: 'academic', label: 'Scholarly publications' },
          { value: 'parliament', label: 'UK Parliament written questions' },
          { value: 'world_bank', label: 'World Bank annual indicator' },
          { value: 'ooni', label: 'OONI connectivity measurements' },
          { value: 'identifier', label: 'Other record identifier' },
        ]}
      />
      {mode === 'academic' && (
        <p className="text-xs text-muted">
          Search publication metadata using your question and collection-plan terms. A country
          filter is not supported.
        </p>
      )}
      {mode === 'parliament' && (
        <p className="text-xs text-muted">
          Search current written-question records using English terms. Choose United Kingdom or All
          countries above.
        </p>
      )}
      {(mode === 'world_bank' || mode === 'ooni') && (
        <SelectField
          label="Record country"
          value={targetCountry}
          onChange={(event) => updatePart(1, event.target.value)}
          options={countryOptions}
        />
      )}
      {mode === 'world_bank' && (
        <>
          <TextField
            label="Indicator code"
            value={parts[2] ?? ''}
            maxLength={80}
            hint="For example, NY.GDP.MKTP.CD for GDP in current US dollars."
            onChange={(event) => updatePart(2, event.target.value.toUpperCase())}
          />
          <div className="grid grid-cols-2 gap-4">
            <TextField
              label="First year"
              type="number"
              min={1900}
              max={2100}
              value={parts[3] ?? ''}
              onChange={(event) => updatePart(3, event.target.value)}
            />
            <TextField
              label="Last year"
              type="number"
              min={1900}
              max={2100}
              value={parts[4] ?? ''}
              onChange={(event) => updatePart(4, event.target.value)}
            />
          </div>
          <p className="text-xs text-muted">
            Up to 20 annual periods. Values reflect the current series, including later revisions.
          </p>
        </>
      )}
      {mode === 'ooni' && (
        <p className="text-xs text-muted">
          Country-level measurement counts, up to 14 days. Collection requires administrator
          approval of the source licence. Anomalies do not prove censorship.
        </p>
      )}
      {mode === 'identifier' && (
        <TextField
          label="Record identifier"
          value={subject}
          maxLength={300}
          hint="Use an explicit identifier supported by the selected source. This is not a fetch URL."
          onChange={(event) => setSubject(event.target.value)}
        />
      )}
      {country &&
        (mode === 'academic' ||
          (mode === 'parliament' && country !== 'GB') ||
          ((mode === 'world_bank' || mode === 'ooni') && targetCountry !== country)) && (
          <Alert tone="warning">
            The country filter conflicts with this record collection. Adjust the country filter or
            the record country before starting.
          </Alert>
        )}
    </fieldset>
  );
}

import { RESEARCH_DEPTHS } from '@/components/research/ResearchDepth';
import { NarrativeLanguageField } from '@/components/languages/NarrativeLanguageField';
import { SourceLanguagePicker } from '@/components/languages/SourceLanguagePicker';
import { useEffect, useState } from 'react';

import { PdfLanguageNotice } from '@/components/reports/PdfLanguageNotice';
import { SelectField, TextField } from '@/components/ui/Field';
import type { Profile } from '@/lib/api/profile';
import { useCountriesStore } from '@/stores/countries';

export type EditableSection = 'profile' | 'research' | 'reports';
interface Props {
  section: EditableSection;
  draft: Profile;
  onChange: <K extends keyof Profile>(field: K, value: Profile[K]) => void;
  sourceLanguages: string;
  onLanguagesChange: (value: string) => void;
}

export function PreferenceFields({
  section,
  draft,
  onChange,
  sourceLanguages,
  onLanguagesChange,
}: Props) {
  const countries = useCountriesStore((state) => state.items);
  const loadCountries = useCountriesStore((state) => state.load);
  const countryError = useCountriesStore((state) => state.error);
  const [timezones] = useState(() =>
    [...new Set(['UTC', draft.timezone, ...Intl.supportedValuesOf('timeZone')])].sort(),
  );
  useEffect(() => {
    if (section === 'research') void loadCountries();
  }, [section, loadCountries]);
  if (section === 'profile')
    return (
      <>
        <TextField
          label="Display name"
          autoComplete="name"
          required
          maxLength={120}
          value={draft.display_name}
          onChange={(event) => onChange('display_name', event.target.value)}
        />
        <SelectField
          label="Timezone"
          value={draft.timezone}
          onChange={(event) => onChange('timezone', event.target.value)}
          options={timezones.map((zone) => ({ value: zone, label: zone.replaceAll('_', ' ') }))}
        />
        <SelectField
          label="Date format"
          value={draft.date_format}
          onChange={(event) =>
            onChange('date_format', event.target.value as Profile['date_format'])
          }
          options={[
            { value: 'day_first', label: 'Day first: 06/09/2026' },
            { value: 'month_first', label: 'Month first: 09/06/2026' },
            { value: 'iso', label: 'ISO: 2026-09-06' },
          ]}
        />
      </>
    );
  if (section === 'research')
    return (
      <>
        <SelectField
          label="Research depth"
          value={draft.research_mode}
          onChange={(event) =>
            onChange('research_mode', event.target.value as Profile['research_mode'])
          }
          options={RESEARCH_DEPTHS.map(({ value, label }) => ({ value, label }))}
        />
        <SelectField
          label="Default date window"
          value={String(draft.research_window_days)}
          onChange={(event) =>
            onChange(
              'research_window_days',
              Number(event.target.value) as Profile['research_window_days'],
            )
          }
          options={[1, 3, 7, 14].map((days) => ({
            value: String(days),
            label: `Past ${days === 1 ? '24 hours' : `${days} days`}`,
          }))}
        />
        <SelectField
          label="Geographic focus"
          value={draft.research_country ?? ''}
          onChange={(event) => onChange('research_country', event.target.value || null)}
          hint={countryError ?? 'You can change this for each research question.'}
          options={[
            { value: '', label: 'Worldwide' },
            ...(draft.research_country &&
            !countries.some((country) => country.iso2 === draft.research_country)
              ? [{ value: draft.research_country, label: draft.research_country }]
              : []),
            ...countries.map((country) => ({ value: country.iso2, label: country.name })),
          ]}
        />
        <SourceLanguagePicker
          label="Source languages"
          selected={sourceLanguages
            .split(',')
            .map((code) => code.trim())
            .filter(Boolean)}
          onChange={(values) => onLanguagesChange(values.join(', '))}
        />
      </>
    );
  return (
    <>
      <NarrativeLanguageField
        hint="Mechanically checked judgement statements remain in English."
        value={draft.report_language}
        onChange={(value) => onChange('report_language', value as Profile['report_language'])}
      />
      <SelectField
        label="Report style"
        value={draft.report_style}
        onChange={(event) =>
          onChange('report_style', event.target.value as Profile['report_style'])
        }
        options={[
          { value: 'briefing', label: 'Concise briefing' },
          { value: 'assessment', label: 'Detailed assessment' },
        ]}
      />
      <SelectField
        label="Preferred export format"
        value={draft.export_format}
        onChange={(event) =>
          onChange('export_format', event.target.value as Profile['export_format'])
        }
        options={[
          { value: 'pdf', label: 'PDF document (.pdf)' },
          { value: 'docx', label: 'Word document (.docx)' },
          { value: 'md', label: 'Markdown (.md)' },
        ]}
      />
      {draft.export_format === 'pdf' && <PdfLanguageNotice language={draft.report_language} />}
    </>
  );
}

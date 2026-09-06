import { SelectField } from '@/components/ui/Field';
import type { ReportRequest } from '@/lib/api/reports';
import { PdfLanguageNotice } from './PdfLanguageNotice';

type Language = NonNullable<ReportRequest['report_language']>;
type Style = NonNullable<ReportRequest['report_style']>;
export function ReportOptions({
  language,
  style,
  onLanguage,
  onStyle,
  disabled = false,
}: {
  language: Language;
  style: Style;
  onLanguage: (value: Language) => void;
  onStyle: (value: Style) => void;
  disabled?: boolean;
}) {
  return (
    <fieldset disabled={disabled} className="space-y-3 border-b border-line pb-5">
      <legend className="mb-3 text-sm font-medium">Report presentation</legend>
      <div className="grid gap-4 sm:grid-cols-2">
        <SelectField
          label="Narrative language"
          value={language}
          onChange={(event) => onLanguage(event.target.value as Language)}
          options={[
            { value: 'en', label: 'English' },
            { value: 'fr', label: 'French' },
            { value: 'de', label: 'German' },
            { value: 'es', label: 'Spanish' },
            { value: 'ar', label: 'Arabic' },
            { value: 'ru', label: 'Russian' },
            { value: 'uk', label: 'Ukrainian' },
            { value: 'zh', label: 'Chinese' },
          ]}
        />
        <SelectField
          label="Report style"
          value={style}
          onChange={(event) => onStyle(event.target.value as Style)}
          options={[
            { value: 'briefing', label: 'Concise briefing' },
            { value: 'assessment', label: 'Detailed assessment' },
          ]}
        />
      </div>
      <p className="text-xs leading-relaxed text-muted">
        Both styles retain citations, evidence limits and uncertainty. Mechanically checked
        judgement statements remain in English.
      </p>
      <PdfLanguageNotice language={language} />
    </fieldset>
  );
}

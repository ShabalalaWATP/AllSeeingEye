import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SelectField } from '@/components/ui/Field';
import { useLanguageCatalogue } from '@/lib/hooks/useLanguageCatalogue';

export function NarrativeLanguageField({
  value,
  onChange,
  hint,
}: {
  value: string;
  onChange: (value: string) => void;
  hint?: string;
}) {
  const catalogue = useLanguageCatalogue();
  const available = catalogue.data?.languages.filter((language) => language.report_supported) ?? [];
  const options = available.map((language) => ({ value: language.code, label: language.label }));
  if (!available.some((language) => language.code === value))
    options.unshift({ value, label: value });
  return (
    <div className="space-y-2">
      <SelectField
        label="Narrative language"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        options={options}
        disabled={catalogue.loading || Boolean(catalogue.error)}
        hint={hint}
      />
      {catalogue.loading && (
        <p role="status" className="text-xs text-muted">
          Loading language options...
        </p>
      )}
      {catalogue.error && (
        <>
          <Alert tone="error">
            Language options could not be loaded. Your selection has been kept.
          </Alert>
          <Button variant="ghost" onClick={() => void catalogue.reload()}>
            Retry languages
          </Button>
        </>
      )}
    </div>
  );
}

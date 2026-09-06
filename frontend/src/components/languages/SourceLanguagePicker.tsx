import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { useLanguageCatalogue } from '@/lib/hooks/useLanguageCatalogue';

export function SourceLanguagePicker({
  selected,
  onChange,
  label = 'Search languages',
}: {
  selected: string[];
  onChange: (value: string[]) => void;
  label?: string;
}) {
  const catalogue = useLanguageCatalogue();
  const languages = catalogue.data?.languages ?? [];
  const unknown = selected.filter(
    (code) => code && !languages.some((language) => language.code === code),
  );
  const options = [
    ...languages.map((language) => ({ code: language.code, label: language.label })),
    ...unknown.map((code) => ({ code, label: code })),
  ];
  const hasUnmappedSelection = languages.some(
    (language) => selected.includes(language.code) && !language.google_news_edition,
  );
  return (
    <fieldset className="space-y-2">
      <legend className="text-sm font-medium">{label}</legend>
      <p className="text-xs text-muted">
        Choose up to eight languages. Coverage depends on the available sources.
      </p>
      {catalogue.loading && (
        <p role="status" className="text-xs text-muted">
          Loading language options...
        </p>
      )}
      {catalogue.error && (
        <>
          <Alert tone="error">
            Language options could not be loaded. Your selections have been kept.
          </Alert>
          <Button variant="ghost" onClick={() => void catalogue.reload()}>
            Retry languages
          </Button>
        </>
      )}
      <div className="grid grid-cols-2 gap-x-4">
        {options.map((language) => (
          <label key={language.code} className="flex min-h-11 items-center gap-2 text-sm">
            <input
              type="checkbox"
              className="h-4 w-4 shrink-0 accent-ember"
              checked={selected.includes(language.code)}
              disabled={
                catalogue.loading ||
                Boolean(catalogue.error) ||
                (selected.length >= 8 && !selected.includes(language.code))
              }
              onChange={(event) =>
                onChange(
                  event.target.checked
                    ? [...selected.filter(Boolean), language.code]
                    : selected.filter((code) => code !== language.code),
                )
              }
            />
            {language.label}
          </label>
        ))}
      </div>
      {hasUnmappedSelection && (
        <p className="text-xs text-muted">
          Some selected languages have no configured Google News edition. Collection uses other
          available sources without substituting a country or script.
        </p>
      )}
    </fieldset>
  );
}

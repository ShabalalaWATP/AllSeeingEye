import { TextAreaField, TextField } from '@/components/ui/Field';
import type { ResearchPlanState } from './useResearchPlan';

export function QueryVariantsEditor({
  plan,
  languages,
  languageName,
  area,
}: {
  plan: ResearchPlanState;
  languages: string[];
  languageName: (code: string) => string;
  area: boolean;
}) {
  return (
    <details className="space-y-3">
      <summary className="cursor-pointer text-sm">Language-specific search terms</summary>
      <p className="text-xs text-muted">
        {area
          ? 'Enter your own language-specific terms where a spatial provider supports them. Area collection does not automatically translate or replan queries.'
          : 'Enter your own terms in each language. These are operator-supplied text, not automatic translations. For blank non-English fields, the run can make one translation call using your configured AI connection (up to 30 seconds). If unavailable or invalid, original terms are used. Translations and their status are saved for review.'}
      </p>
      {languages.map((language) => (
        <section key={language} className="space-y-3 border-t border-line pt-3">
          <TextAreaField
            key={language}
            label={`Search terms: ${languageName(language)}`}
            dir="auto"
            value={plan.variantText[language] ?? ''}
            rows={2}
            maxLength={1012}
            hint="One phrase per line, up to 12."
            onChange={(event) =>
              plan.setVariantText((current) => ({ ...current, [language]: event.target.value }))
            }
          />
          <TextAreaField
            label={`Translation originals: ${languageName(language)}`}
            dir="auto"
            rows={2}
            maxLength={1012}
            hint="Optional exact original phrases, aligned one per translated line. Older unlinked translations remain supported."
            value={plan.variantOriginalText[language] ?? ''}
            onChange={(event) =>
              plan.setVariantOriginalText((current) => ({
                ...current,
                [language]: event.target.value,
              }))
            }
          />
          <details className="space-y-3">
            <summary className="cursor-pointer text-sm">
              Supply transliteration: {languageName(language)}
            </summary>
            <p className="text-xs text-muted">
              Enter your own script rendering. No automatic transliteration is performed. It remains
              separate from the translation above and uses the same collection budget. Link original
              and outbound phrases line by line; unsupported source/script routing is shown in the
              preview.
            </p>
            <TextAreaField
              label={`Transliteration originals: ${languageName(language)}`}
              dir="auto"
              rows={2}
              maxLength={1012}
              hint="Exact phrases from Original search terms, one per line."
              value={plan.transliterations.drafts[language]?.original ?? ''}
              onChange={(event) =>
                plan.transliterations.update(language, { original: event.target.value })
              }
            />
            <TextAreaField
              label={`Transliterated terms: ${languageName(language)}`}
              dir="auto"
              rows={2}
              maxLength={1012}
              hint="One outbound phrase per original line, in the same order."
              value={plan.transliterations.drafts[language]?.transformed ?? ''}
              onChange={(event) =>
                plan.transliterations.update(language, { transformed: event.target.value })
              }
            />
            <div className="grid gap-3 sm:grid-cols-2">
              <TextField
                label={`Original script: ${languageName(language)}`}
                maxLength={4}
                hint="Required four-letter ISO 15924 code, such as Arab."
                value={plan.transliterations.drafts[language]?.sourceScript ?? ''}
                onChange={(event) =>
                  plan.transliterations.update(language, { sourceScript: event.target.value })
                }
              />
              <TextField
                label={`Transliteration script: ${languageName(language)}`}
                maxLength={4}
                hint="Required four-letter ISO 15924 code, such as Latn."
                value={plan.transliterations.drafts[language]?.targetScript ?? ''}
                onChange={(event) =>
                  plan.transliterations.update(language, { targetScript: event.target.value })
                }
              />
            </div>
            <TextField
              label={`Transliteration method: ${languageName(language)}`}
              maxLength={120}
              hint="Name the convention you used; required for explicit transliteration."
              value={plan.transliterations.drafts[language]?.method ?? ''}
              onChange={(event) =>
                plan.transliterations.update(language, { method: event.target.value })
              }
            />
          </details>
        </section>
      ))}
    </details>
  );
}

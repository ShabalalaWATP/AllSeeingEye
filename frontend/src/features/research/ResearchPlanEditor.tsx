import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { TextAreaField } from '@/components/ui/Field';
import { useLanguageCatalogue } from '@/lib/hooks/useLanguageCatalogue';
import type { ResearchPlanState } from './useResearchPlan';

export function ResearchPlanEditor({
  plan,
  languages,
}: {
  plan: ResearchPlanState;
  languages: string[];
}) {
  const catalogue = useLanguageCatalogue();
  const sources = [
    ...new Map(plan.snapshot?.tasks.map((task) => [task.source_id, task]) ?? []).values(),
  ];
  const languageName = (code: string) =>
    catalogue.data?.languages.find((entry) => entry.code === code)?.label ?? code;
  return (
    <details className="min-w-0 border-b border-line pb-5">
      <summary className="cursor-pointer py-2 text-sm font-medium">
        Collection plan (optional)
      </summary>
      <div className="mt-4 space-y-5">
        <p className="text-xs leading-relaxed text-muted">
          Choose public sources and exact search terms before collection. This preview makes no
          model calls or source requests. The reporting window advances to the time the run starts.
        </p>
        <fieldset disabled={plan.busy} className="space-y-5">
          <label className="flex min-h-11 items-center gap-2 text-sm">
            <input
              type="checkbox"
              className="h-4 w-4 accent-ember"
              checked={plan.customTerms}
              onChange={(event) => plan.setCustomTerms(event.target.checked)}
            />
            Supply exact search terms
          </label>
          {plan.customTerms ? (
            <TextAreaField
              label="Original search terms"
              dir="auto"
              hint="One phrase per line, up to 12. These exact terms will be sent to the selected sources unless a language-specific override is supplied."
              value={plan.termsText}
              maxLength={1012}
              rows={3}
              onChange={(event) => plan.setTermsText(event.target.value)}
            />
          ) : (
            <p className="text-xs text-muted">
              Original search terms are planned during research. This preview cannot predict them;
              supply exact terms to review the queries in advance.
            </p>
          )}
          <details className="space-y-3">
            <summary className="cursor-pointer text-sm">Language-specific search terms</summary>
            <p className="text-xs text-muted">
              Enter your own terms in each language. These are operator-supplied text, not automatic
              translations. Blank fields use the original terms.
            </p>
            {languages.map((language) => (
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
            ))}
          </details>
          {sources.length > 0 && (
            <fieldset className="space-y-2">
              <legend className="text-sm font-medium">Public sources</legend>
              {sources.map((source) => (
                <label className="flex min-h-11 items-center gap-2 text-sm" key={source.source_id}>
                  <input
                    type="checkbox"
                    className="h-4 w-4 accent-ember"
                    checked={plan.sourceIds?.includes(source.source_id) ?? source.selected}
                    onChange={(event) => plan.selectSource(source.source_id, event.target.checked)}
                  />
                  {source.source_name}
                </label>
              ))}
              <Button
                variant="ghost"
                disabled={plan.sourceIds === null}
                onClick={plan.resetSources}
              >
                Use default sources
              </Button>
            </fieldset>
          )}
        </fieldset>
        {plan.sourceIds?.length === 0 && (
          <Alert tone="warning">
            No public sources selected. This run will rely on existing evidence.
          </Alert>
        )}
        {plan.error && <Alert tone="error">{plan.error}</Alert>}
        {plan.customised && !plan.current && (
          <p role="status" className="text-sm text-muted">
            Preview these changes before starting research.
          </p>
        )}
        <Button variant="secondary" busy={plan.busy} onClick={() => void plan.preview()}>
          {plan.busy ? 'Preparing preview...' : 'Preview collection plan'}
        </Button>
        {plan.snapshot && (
          <section aria-label="Collection plan preview" className="space-y-3">
            <h3 className="text-sm font-medium">
              {plan.current ? 'Current preview' : 'Previous preview, settings have changed'}
            </h3>
            <p className="text-xs text-muted">
              Up to {plan.snapshot.request_limit} requests · {plan.snapshot.seconds_limit} seconds ·{' '}
              {plan.snapshot.item_limit} evidence items. Plan policy {plan.snapshot.policy_version}.
            </p>
            <p className="text-xs text-muted">
              The execution receipt records which sources actually responded and what was collected.
            </p>
            <ul className="divide-y divide-line text-xs">
              {plan.snapshot.tasks
                .filter((task) => task.selected)
                .map((task, index) => (
                  <li
                    key={`${task.source_id}:${task.language ?? ''}:${index}`}
                    className="space-y-1 py-3"
                  >
                    <p className="font-medium text-text">
                      {task.source_name}
                      {task.language ? ` / ${languageName(task.language)}` : ''}
                    </p>
                    <p className="break-words text-muted">
                      {task.terms.length
                        ? task.terms.join(' · ')
                        : 'No exact terms available in this preview'}
                    </p>
                    <p className="text-muted">
                      {task.provenance === 'operator_supplied_variant'
                        ? 'Your language-specific terms'
                        : 'Original terms'}{' '}
                      · {task.temporal_scope}
                    </p>
                    {!task.supported && (
                      <p className="text-amber">
                        Unavailable for these preview inputs. Source support is checked again when
                        the run starts.
                      </p>
                    )}
                  </li>
                ))}
            </ul>
          </section>
        )}
      </div>
    </details>
  );
}

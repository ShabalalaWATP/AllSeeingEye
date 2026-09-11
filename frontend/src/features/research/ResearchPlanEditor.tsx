import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { TextAreaField } from '@/components/ui/Field';
import { useLanguageCatalogue } from '@/lib/hooks/useLanguageCatalogue';
import type { ResearchPlanState } from './useResearchPlan';
import { QueryVariantDetails } from '@/components/reports/QueryVariantDetails';
import { RegistryLookupDetails } from '@/components/reports/RegistryLookupDetails';
import { PlannedTasksEditor } from './PlannedTasksEditor';
import { QueryVariantsEditor } from './QueryVariantsEditor';

export function ResearchPlanEditor({
  plan,
  languages,
  area = false,
  historical = false,
  fixed = false,
}: {
  plan: ResearchPlanState;
  languages: string[];
  area?: boolean;
  historical?: boolean;
  fixed?: boolean;
}) {
  const catalogue = useLanguageCatalogue();
  const sources = (plan.snapshot?.tasks ?? []).filter(
    (task, index, all) => all.findIndex((row) => row.source_id === task.source_id) === index,
  );
  const languageName = (code: string) =>
    catalogue.data?.languages.find((entry) => entry.code === code)?.label ?? code;
  return (
    <details className="min-w-0 border-b border-line pb-5">
      <summary className="cursor-pointer py-2 text-sm font-medium">
        Collection plan {area || historical ? '(required)' : '(optional)'}
      </summary>
      <div className="mt-4 space-y-5">
        <p className="text-xs leading-relaxed text-muted">
          Choose public sources and exact search terms before collection. This preview makes no
          model calls or source requests.{' '}
          {area
            ? 'The chosen area and fixed dates are used for preview and collection.'
            : historical
              ? 'The chosen commitment years are fixed for preview and collection.'
              : fixed
                ? 'Your chosen dates stay fixed for preview and collection.'
                : 'The reporting window advances to the time the run starts.'}
          {area
            ? ' Area collection only uses providers that explicitly support this geometry. Empty results do not prove absence.'
            : ' General research can review its first results using the configured AI connection. It may revise an empty search or investigate a possible conflict, or stop when the question appears covered and required tasks are finished. This uses one bounded review within the same collection budget. Scope and explicit tasks stay fixed; the decision and passes are saved for review.'}
        </p>
        <p className="text-xs leading-relaxed text-muted">
          During public-source research, the configured AI connection can propose identity
          hypotheses and searches for conflicting evidence or distinguishing identifiers, where
          selected sources support exact task queries. These additions share the existing task and
          collection limits. Your sources, scope and explicit tasks remain in effect. This preview
          does not call that model or predict its proposals; the execution receipt records what was
          proposed, added and actually attempted.
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
              hint="One phrase per line, up to 12. Original phrases are retained. Supply language-specific overrides to control translated source queries."
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
          <QueryVariantsEditor
            plan={plan}
            languages={languages}
            languageName={languageName}
            area={area}
          />
          <PlannedTasksEditor
            value={plan.tasks}
            sources={sources.map((source) => ({
              ...source,
              registry_options: plan.registryOptionsCurrent ? (source.registry_options ?? []) : [],
              selected: plan.sourceIds?.includes(source.source_id) ?? source.selected,
            }))}
          />
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
            {area
              ? 'Select at least one supported spatial source and preview again. Area research does not reuse parent or global evidence.'
              : 'No public sources selected. This run will rely on existing evidence.'}
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
                    {task.purpose !== 'baseline' && (
                      <p className="text-cyan">
                        {task.purpose === 'challenge'
                          ? 'Conflicting evidence search'
                          : 'Identity candidate check'}
                        {task.candidate_id
                          ? ` · Hypothesis: ${plan.snapshot?.candidate_hypotheses?.find((candidate) => candidate.id === task.candidate_id)?.label ?? task.candidate_id}`
                          : ''}
                      </p>
                    )}
                    {task.query_variant && <QueryVariantDetails value={task.query_variant} />}
                    {task.registry_lookup && <RegistryLookupDetails value={task.registry_lookup} />}
                    <p className="break-words text-muted">
                      {task.terms.length
                        ? task.terms.join(' · ')
                        : task.registry_lookup
                          ? 'Exact identifier route; no translated search terms'
                          : 'No exact terms available in this preview'}
                    </p>
                    <p className="text-muted">
                      {task.registry_lookup
                        ? 'Exact operator-supplied identifier'
                        : task.provenance === 'operator_supplied_variant'
                          ? 'Your language-specific terms'
                          : task.provenance === 'operator_supplied_task'
                            ? 'Your exact task terms'
                            : 'Original terms'}{' '}
                      · {task.temporal_scope}
                    </p>
                    {!task.supported && (
                      <p className="text-amber">
                        Unavailable for these preview inputs. Source support is checked again when
                        the run starts.
                      </p>
                    )}
                    {plan.snapshot?.area && (
                      <p className="text-muted">
                        {task.spatial_supported ? 'Area query supported' : 'Area query unsupported'}
                        : {task.spatial_scope}
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

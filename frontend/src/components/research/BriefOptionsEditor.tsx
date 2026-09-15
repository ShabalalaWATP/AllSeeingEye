import { Button } from '@/components/ui/Button';
import { SelectField, TextField } from '@/components/ui/Field';
import type { BriefDraft } from '@/lib/api/researchBriefSchema';

import { BriefListField } from './BriefListField';

const optionalNumber = (value: string) => (value === '' ? null : Number(value));

export function BriefOptionsEditor({
  draft,
  change,
}: {
  draft: BriefDraft;
  change: (next: BriefDraft) => void;
}) {
  const { collection, limits, monitoring } = draft;
  const setCollection = (patch: Partial<typeof collection>) =>
    change({ ...draft, collection: { ...collection, ...patch } });
  const setLimits = (patch: Partial<typeof limits>) =>
    change({ ...draft, limits: { ...limits, ...patch } });
  const setMonitoring = (patch: Partial<typeof monitoring>) =>
    change({ ...draft, monitoring: { ...monitoring, ...patch } });
  return (
    <div className="space-y-6">
      <fieldset className="min-w-0 grid gap-4 border-t border-line pt-4 sm:grid-cols-2">
        <legend className="px-1 text-sm font-semibold">Collection</legend>

        <BriefListField
          label="Search terms, one per line"
          multiline
          values={collection.terms ?? []}
          change={(terms) => setCollection({ terms: terms.length ? terms : null })}
        />
        <SelectField
          label="Source policy"
          value={collection.source_policy}
          onChange={(event) => {
            const source_policy = event.target.value as typeof collection.source_policy;
            setCollection({
              source_policy,
              source_ids: source_policy === 'selected_only' ? [] : null,
            });
          }}
          options={[
            { value: 'all_eligible', label: 'All eligible sources' },
            { value: 'selected_only', label: 'Selected sources only' },
          ]}
        />
        {collection.source_policy === 'selected_only' && (
          <BriefListField
            label="Selected source IDs, one per line"
            multiline
            values={collection.source_ids ?? []}
            change={(source_ids) => setCollection({ source_ids })}
          />
        )}
        <div className="space-y-2 sm:col-span-2">
          {(
            [
              ['web_search', 'Allow fresh web search'],
              ['require_primary', 'Require primary sources'],
              ['require_local', 'Require local sources'],
              ['require_opposition', 'Require opposing evidence'],
            ] as const
          ).map(([key, label]) => (
            <label key={key} className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={collection[key]}
                onChange={(event) => setCollection({ [key]: event.target.checked })}
              />
              {label}
            </label>
          ))}
          <p className="text-xs leading-relaxed text-muted">
            Fresh web search sends authorised query text to the configured provider. Private inputs
            retain their separate disclosure permissions.
          </p>
        </div>
      </fieldset>
      <fieldset className="min-w-0 grid gap-4 border-t border-line pt-4 sm:grid-cols-2">
        <legend className="px-1 text-sm font-semibold">Limits and monitoring</legend>
        {(
          [
            ['max_passes', 'Maximum passes', 2],
            ['max_external_operations', 'Maximum external operations', 32],
            ['max_model_calls', 'Maximum model calls', 24],
            ['max_output_tokens', 'Maximum output tokens', 256000],
            ['max_collection_seconds', 'Maximum collection seconds', 240],
          ] as const
        ).map(([key, label, maximum]) => (
          <TextField
            key={key}
            label={label}
            type="number"
            min={1}
            max={maximum}
            value={limits[key] ?? ''}
            onChange={(event) => setLimits({ [key]: optionalNumber(event.target.value) })}
          />
        ))}
        <SelectField
          label="Prefer novel evidence"
          value={monitoring.prefer_novelty === null ? '' : String(monitoring.prefer_novelty)}
          onChange={(event) =>
            setMonitoring({
              prefer_novelty: event.target.value === '' ? null : event.target.value === 'true',
            })
          }
          options={[
            { value: '', label: 'No preference' },
            { value: 'true', label: 'Yes' },
            { value: 'false', label: 'No' },
          ]}
        />
        <BriefListField
          label="Review conditions, one per line"
          multiline
          values={monitoring.review_conditions}
          change={(review_conditions) => setMonitoring({ review_conditions })}
        />
        <div className="space-y-3 sm:col-span-2">
          <p className="text-sm font-medium">Monitoring indicators</p>
          {monitoring.indicators.map((indicator, index) => (
            <div key={index} className="grid gap-2 sm:grid-cols-[10rem_minmax(0,1fr)_auto]">
              <TextField
                label={`Indicator ${index + 1} ID`}
                maxLength={64}
                value={indicator.id}
                onChange={(event) =>
                  setMonitoring({
                    indicators: monitoring.indicators.map((row, at) =>
                      at === index ? { ...row, id: event.target.value } : row,
                    ),
                  })
                }
              />
              <TextField
                label={`Indicator ${index + 1} condition`}
                maxLength={500}
                value={indicator.condition}
                onChange={(event) =>
                  setMonitoring({
                    indicators: monitoring.indicators.map((row, at) =>
                      at === index ? { ...row, condition: event.target.value } : row,
                    ),
                  })
                }
              />
              <Button
                variant="ghost"
                onClick={() =>
                  setMonitoring({
                    indicators: monitoring.indicators.filter((_, at) => at !== index),
                  })
                }
              >
                Remove indicator {index + 1}
              </Button>
            </div>
          ))}
          <Button
            variant="secondary"
            disabled={monitoring.indicators.length >= 12}
            onClick={() =>
              setMonitoring({
                indicators: [
                  ...monitoring.indicators,
                  { id: `indicator-${monitoring.indicators.length + 1}`, condition: '' },
                ],
              })
            }
          >
            Add indicator
          </Button>
        </div>
      </fieldset>
      {(collection.query_variants.length > 0 ||
        collection.candidate_hypotheses.length > 0 ||
        collection.planned_tasks.length > 0 ||
        draft.private_inputs.length > 0) && (
        <p className="text-sm text-muted">
          Saved translations, planned tasks, hypotheses and private references remain pinned to this
          revision. Review or renew private access before admission.
        </p>
      )}
    </div>
  );
}

import { SelectField, TextField } from '@/components/ui/Field';
import type { BriefDraft } from '@/lib/api/researchBriefSchema';

import { BriefListField } from './BriefListField';

function datetimeLocal(value: string | null) {
  return value ? new Date(value).toISOString().slice(0, 16) : '';
}
function utc(value: string) {
  return value ? new Date(`${value}Z`).toISOString() : null;
}

export function BriefScopeEditor({
  draft,
  change,
}: {
  draft: BriefDraft;
  change: (next: BriefDraft) => void;
}) {
  const { scope, observation } = draft;
  const setScope = (patch: Partial<typeof scope>) =>
    change({ ...draft, scope: { ...scope, ...patch } });
  const setObservation = (patch: Partial<typeof observation>) =>
    change({ ...draft, observation: { ...observation, ...patch } });
  return (
    <div className="space-y-4">
      {scope.map_view_id && scope.map_revision_id && (
        <p className="rounded border border-line p-3 text-sm">
          Exact saved map revision pinned: {scope.map_revision_id}. Area disclosure is controlled
          below.
        </p>
      )}
      {(scope.area !== null || scope.map_origin !== null) && (
        <p className="rounded border border-line p-3 text-sm">
          Exact saved polygon is pinned to this brief.
        </p>
      )}
      {(scope.area !== null || scope.map_origin !== null || scope.map_view_id !== null) && (
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={scope.disclose_area_to_provider}
            onChange={(event) => setScope({ disclose_area_to_provider: event.target.checked })}
          />
          Permit area and period disclosure to selected providers
        </label>
      )}
      <BriefListField
        label="Country codes, comma separated"
        values={scope.country_isos}
        uppercase
        disabled={
          scope.focus !== 'general' || !!scope.area || !!scope.map_origin || !!scope.map_view_id
        }
        change={(country_isos) => setScope({ country_isos })}
      />
      <SelectField
        label="Research focus"
        value={scope.focus}
        disabled={!!scope.area || !!scope.map_origin || !!scope.map_view_id}
        onChange={(event) =>
          setScope({
            focus: event.target.value as typeof scope.focus,
            country_isos: event.target.value === 'general' ? scope.country_isos : [],
          })
        }
        options={[
          { value: 'general', label: 'General' },
          { value: 'company', label: 'Company' },
          { value: 'domain', label: 'Domain' },
          { value: 'document', label: 'Private document' },
          { value: 'media', label: 'Private media' },
        ]}
      />
      <TextField
        label="Research subject"
        hint={
          scope.focus === 'general' ? 'Optional named subject or required preset input.' : undefined
        }
        value={scope.subject ?? ''}
        maxLength={300}
        onChange={(event) => setScope({ subject: event.target.value || null })}
      />
      {!scope.area && !scope.map_origin && !scope.map_view_id && (
        <details className="border-t border-line pt-3">
          <summary className="cursor-pointer text-sm font-medium">Additional scope filters</summary>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <TextField
              label="Conflict ID"
              maxLength={120}
              value={scope.conflict_id ?? ''}
              onChange={(event) => setScope({ conflict_id: event.target.value || null })}
            />
            <TextField
              label="Hazard"
              maxLength={40}
              value={scope.hazard ?? ''}
              onChange={(event) => setScope({ hazard: event.target.value || null })}
            />
            <BriefListField
              label="Event categories, comma separated"
              values={scope.categories}
              change={(categories) => setScope({ categories })}
            />
            <TextField
              label="Collection plan ID"
              value={scope.plan_id ?? ''}
              onChange={(event) => setScope({ plan_id: event.target.value || null })}
            />
          </div>
        </details>
      )}
      <SelectField
        label="Observation period"
        value={observation.policy}
        onChange={(event) => {
          const policy = event.target.value as typeof observation.policy;
          setObservation({
            policy,
            since: null,
            until: null,
            lookback_hours: policy === 'relative' ? 24 : null,
          });
        }}
        options={[
          { value: 'relative', label: 'Rolling window' },
          { value: 'explicit', label: 'Exact historical interval' },
          { value: 'template_default', label: 'Product default' },
        ]}
      />
      {observation.policy === 'relative' && (
        <TextField
          label="Lookback hours"
          type="number"
          min={1}
          max={24 * 730}
          value={observation.lookback_hours ?? ''}
          onChange={(event) => setObservation({ lookback_hours: Number(event.target.value) })}
        />
      )}
      {observation.policy === 'explicit' && (
        <div className="grid gap-4 sm:grid-cols-2">
          <TextField
            label="Observation start (UTC)"
            type="datetime-local"
            value={datetimeLocal(observation.since)}
            onChange={(event) => setObservation({ since: utc(event.target.value) })}
          />
          <TextField
            label="Observation end (UTC)"
            type="datetime-local"
            value={datetimeLocal(observation.until)}
            onChange={(event) => setObservation({ until: utc(event.target.value) })}
          />
        </div>
      )}
      <SelectField
        label="Evidence date basis"
        value={observation.time_basis ?? ''}
        onChange={(event) =>
          setObservation({
            time_basis: (event.target.value || null) as typeof observation.time_basis,
          })
        }
        options={[
          { value: '', label: 'Product default' },
          { value: 'publication', label: 'Published' },
          { value: 'acquisition_or_publication', label: 'Acquired or published' },
          { value: 'recorded_time', label: 'Recorded history' },
        ]}
      />
      <TextField
        label="Forecast horizon in days (optional)"
        hint="Future outlook only. This does not change the observation dates above."
        type="number"
        min={1}
        max={366}
        value={observation.forecast_horizon_days ?? ''}
        onChange={(event) =>
          setObservation({
            forecast_horizon_days: event.target.value ? Number(event.target.value) : null,
          })
        }
      />
      <BriefListField
        label="Reviewed aliases, one per line"
        multiline
        values={scope.reviewed_aliases}
        change={(reviewed_aliases) => setScope({ reviewed_aliases })}
      />
    </div>
  );
}

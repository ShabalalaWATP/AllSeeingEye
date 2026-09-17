import { useState } from 'react';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SelectField, TextField } from '@/components/ui/Field';
import { useModelSetupDiscovery } from './ModelSetupDiscovery';
import type { ModelSetupState } from './ModelSetupState';

export function ModelSetupModel({ state }: { state: ModelSetupState }) {
  const [manual, setManual] = useState(state.fields.provider === 'bedrock');
  const [search, setSearch] = useState('');
  const catalogue = useModelSetupDiscovery(
    state.fields.provider !== 'bedrock',
    state.fields.baseUrl,
    state.fields.apiKey,
    state.storedKey ? state.draft?.id : undefined,
  );
  const model = state.fields.model;
  const choose = (value: string) =>
    state.change({ model: value, effort: value === model ? state.fields.effort : '' });
  const filtered = catalogue.models.filter((id) => id.toLowerCase().includes(search.toLowerCase()));
  const missingModel = !!model && !catalogue.models.includes(model);
  return (
    <div className="space-y-4">
      {state.fields.provider !== 'bedrock' && (
        <>
          {catalogue.busy && (
            <p role="status" className="text-sm text-muted">
              {catalogue.attempts > 1
                ? `Retrying model discovery (${catalogue.attempts}/3)…`
                : 'Finding models available to your account…'}
            </p>
          )}
          {catalogue.error && (
            <Alert tone="warning">
              Model discovery is unavailable. {catalogue.error} Refresh the list or enter an exact
              model ID.
            </Alert>
          )}
          {!catalogue.busy && !catalogue.error && (
            <p className="text-xs text-muted">
              {catalogue.models.length} account models found. The test checks whether your choice
              supports research.
            </p>
          )}
          {!manual && catalogue.models.length > 0 && (
            <>
              <TextField
                label="Search models"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Filter by model name"
              />
              <SelectField
                label="Account model"
                name="model"
                value={model}
                required
                onChange={(event) => choose(event.target.value)}
                options={[
                  { value: '', label: 'Choose a model' },
                  ...(model && !filtered.includes(model)
                    ? [
                        {
                          value: model,
                          label: `${model}${missingModel ? ' (entered manually)' : ''}`,
                        },
                      ]
                    : []),
                  ...filtered.map((id) => ({ value: id, label: id })),
                ]}
              />
            </>
          )}
          <div className="flex flex-wrap gap-2">
            <Button variant="ghost" disabled={catalogue.busy} onClick={catalogue.refresh}>
              Refresh models
            </Button>
            <Button variant="ghost" onClick={() => setManual((value) => !value)}>
              {manual ? 'Use account model list' : 'Enter model ID manually'}
            </Button>
          </div>
        </>
      )}
      {(manual || (!catalogue.busy && catalogue.models.length === 0)) && (
        <TextField
          label={
            state.fields.provider === 'bedrock' ? 'Model or inference profile ID' : 'Exact model ID'
          }
          name="model"
          value={model}
          onChange={(event) => choose(event.target.value)}
          required
          maxLength={state.fields.provider === 'bedrock' ? 2048 : 120}
          hint={
            state.fields.provider === 'bedrock'
              ? 'Copy a Converse-compatible model or inference profile ID from AWS. Bedrock does not provide account discovery here.'
              : 'Use the exact ID supplied by your provider.'
          }
        />
      )}
    </div>
  );
}

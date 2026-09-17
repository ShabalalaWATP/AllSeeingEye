import { useState } from 'react';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SelectField, TextField } from '@/components/ui/Field';
import type { LlmProfile } from '@/lib/api/llm';
export function LlmModelSelection({
  bedrock,
  models,
  model,
  setModel,
  effort,
  setEffort,
  embeddings,
  discovery,
  onDiscover,
  canDiscover,
}: {
  bedrock: boolean;
  models: readonly string[];
  model: string;
  setModel: (value: string) => void;
  effort: NonNullable<LlmProfile['reasoning_effort']> | '';
  setEffort: (value: NonNullable<LlmProfile['reasoning_effort']> | '') => void;
  embeddings: boolean;
  discovery: { busy: boolean; error: string | null; loaded: boolean };
  onDiscover: () => void;
  canDiscover: boolean;
}) {
  const [search, setSearch] = useState('');
  const [manual, setManual] = useState(false);
  const filtered = models.filter((value) => value.toLowerCase().includes(search.toLowerCase()));
  const showManual =
    bedrock || manual || models.length === 0 || (!!model && !models.includes(model));
  return (
    <section className="space-y-4" aria-label="Choose and test model">
      {!bedrock && (
        <>
          <Button variant="ghost" disabled={!canDiscover || discovery.busy} onClick={onDiscover}>
            {discovery.busy ? 'Loading account models...' : 'Refresh account models'}
          </Button>
          {models.length > 0 && !showManual && (
            <div className="grid gap-3 md:grid-cols-2">
              <TextField
                label="Search account models"
                value={search}
                placeholder="Filter by model name"
                onChange={(event) => setSearch(event.target.value)}
              />
              <SelectField
                label="Models returned by this account"
                name="model"
                value={model}
                required
                options={[
                  { value: '', label: 'Select an available model' },
                  ...(model && !filtered.includes(model) ? [{ value: model, label: model }] : []),
                  ...filtered.map((value) => ({ value, label: value })),
                ]}
                onChange={(event) => {
                  if (event.target.value) setModel(event.target.value);
                }}
              />
            </div>
          )}
          {discovery.loaded && (
            <p role="status" className="text-xs text-muted">
              {models.length} models returned by this account. Not every model supports text
              research; the connection test checks compatibility.
            </p>
          )}
          {discovery.error && (
            <Alert tone="warning">
              {discovery.error} You can retry or enter a model ID manually.
            </Alert>
          )}
          {models.length > 0 && (
            <Button
              variant="ghost"
              onClick={() => {
                if (showManual) setModel('');
                setManual(!showManual);
              }}
            >
              {showManual ? 'Choose from account models' : 'Enter a model ID manually'}
            </Button>
          )}
        </>
      )}
      <div className="grid gap-4 md:grid-cols-2">
        {showManual && (
          <TextField
            name="model"
            label={bedrock ? 'Model or inference profile ID' : 'Model ID'}
            value={model}
            onChange={(event) => setModel(event.target.value)}
            required
            maxLength={bedrock ? 2048 : 120}
            placeholder={bedrock ? 'e.g. openai.gpt-oss-120b-1:0' : undefined}
            hint={
              bedrock
                ? 'Copy a Converse-compatible model or inference profile ID from AWS. Bedrock catalogue discovery is not supported.'
                : 'Choose an account model above, or enter an exact ID.'
            }
          />
        )}
        {!bedrock && !embeddings && (
          <SelectField
            label="Reasoning effort"
            value={effort}
            onChange={(event) => setEffort(event.target.value as typeof effort)}
            options={[
              { value: '', label: 'Provider default' },
              ...['none', 'minimal', 'low', 'medium', 'high', 'xhigh', 'max'].map((value) => ({
                value,
                label:
                  value === 'xhigh' ? 'Extra high' : value.charAt(0).toUpperCase() + value.slice(1),
              })),
            ]}
            hint="Start with Provider default. Higher levels may take longer and cost more. Availability depends on the model."
          />
        )}
      </div>
      {bedrock && (
        <p className="text-xs text-muted">
          Reasoning uses the provider default. Bedrock uses API keys; IAM roles are not supported.
        </p>
      )}
    </section>
  );
}

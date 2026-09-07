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
  canTest,
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
  canTest: boolean;
}) {
  const [search, setSearch] = useState('');
  const filtered = models.filter((value) => value.toLowerCase().includes(search.toLowerCase()));
  return (
    <section className="space-y-4 border-t border-line pt-4" aria-label="Choose and test model">
      <h3 className="text-sm font-semibold">2. Choose and test</h3>
      {!bedrock && (
        <>
          <Button
            variant="secondary"
            disabled={!canDiscover || discovery.busy}
            onClick={onDiscover}
          >
            {discovery.busy ? 'Loading account models...' : 'Refresh account models'}
          </Button>
          {models.length > 0 && (
            <div className="grid gap-3 md:grid-cols-2">
              <TextField
                label="Search account models"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
              <SelectField
                label="Models returned by this account"
                value={filtered.includes(model) ? model : ''}
                options={[
                  { value: '', label: 'Choose a model or enter its ID below' },
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
              {models.length} models returned by this account. Catalogue entries can include models
              unsuitable for text research; test the selected configuration.
            </p>
          )}
          {discovery.error && (
            <Alert tone="warning">
              {discovery.error} You can retry or enter a model ID manually.
            </Alert>
          )}
        </>
      )}
      <div className="grid gap-4 md:grid-cols-2">
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
        {!bedrock && !embeddings && (
          <SelectField
            label="Reasoning effort"
            value={effort}
            onChange={(event) => setEffort(event.target.value as typeof effort)}
            options={[
              { value: '', label: 'Provider default' },
              ...[
                'none',
                ...(model === 'gpt-5.6-luna' ? [] : ['minimal']),
                'low',
                'medium',
                'high',
                'xhigh',
                'max',
              ].map((value) => ({
                value,
                label:
                  value === 'xhigh' ? 'Extra high' : value.charAt(0).toUpperCase() + value.slice(1),
              })),
            ]}
            hint="Max can take longer and use more tokens. A successful test checks actual compatibility."
          />
        )}
      </div>
      {bedrock && (
        <p className="text-xs text-muted">
          Reasoning uses the provider default. Bedrock uses API keys; IAM roles are not supported.
        </p>
      )}
      {canTest && (
        <div className="space-y-2">
          <Button type="submit" name="action" value="test">
            Test connection
          </Button>
          <p className="text-xs text-muted">
            Saves an inactive draft and sends a short compatibility request. Provider usage charges
            may apply.
          </p>
        </div>
      )}
    </section>
  );
}

import { useState } from 'react';
import type { SyntheticEvent } from 'react';

import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { TextField } from '@/components/ui/Field';
import { LLM_ROLES } from '@/lib/api/llm';
import type { LlmProfile, LlmProfileInput, LlmRole } from '@/lib/api/llm';

const ROLE_LABELS: Record<LlmRole, string> = {
  direction: 'Direction',
  assessment: 'Assessment',
  devil: "Devil's advocate",
  translation: 'Translation',
  embeddings: 'Embeddings',
};

export interface LlmProfileFormProps {
  /** Editing an existing profile; absent when creating. */
  initial?: LlmProfile | undefined;
  busy: boolean;
  error: string | null;
  onSubmit: (input: LlmProfileInput) => void;
  onCancel: () => void;
}

/** Create or edit a profile. The key field is write-only: blank keeps the stored key. */
export function LlmProfileForm({ initial, busy, error, onSubmit, onCancel }: LlmProfileFormProps) {
  const [name, setName] = useState(initial?.name ?? '');
  const [baseUrl, setBaseUrl] = useState(initial?.base_url ?? '');
  const [model, setModel] = useState(initial?.model ?? '');
  const [apiKey, setApiKey] = useState('');
  const [roles, setRoles] = useState<LlmRole[]>(initial?.roles ?? ['assessment']);
  const [maxTokens, setMaxTokens] = useState(String(initial?.max_output_tokens ?? 4000));
  const [temperature, setTemperature] = useState(String(initial?.temperature ?? 0.2));
  const [enabled, setEnabled] = useState(initial?.enabled ?? true);

  const toggleRole = (role: LlmRole) => {
    setRoles((current) =>
      current.includes(role) ? current.filter((item) => item !== role) : [...current, role],
    );
  };

  const submit = (event: SyntheticEvent<HTMLFormElement>) => {
    event.preventDefault();
    const input: LlmProfileInput = {
      name: name.trim(),
      base_url: baseUrl.trim(),
      model: model.trim(),
      roles,
      max_output_tokens: Number(maxTokens),
      temperature: Number(temperature),
      enabled,
    };
    if (apiKey.trim() !== '') input.api_key = apiKey.trim();
    onSubmit(input);
  };

  return (
    <form
      onSubmit={submit}
      aria-label={initial === undefined ? 'New model profile' : `Edit ${initial.name}`}
      className="flex flex-col gap-4 rounded-card border border-line bg-surface p-4"
    >
      <div className="grid gap-4 md:grid-cols-2">
        <TextField
          label="Name"
          value={name}
          onChange={(event) => {
            setName(event.target.value);
          }}
          required
          maxLength={80}
        />
        <TextField
          label="Model"
          value={model}
          onChange={(event) => {
            setModel(event.target.value);
          }}
          required
          maxLength={120}
          placeholder="gpt-4.1-mini or llama3.1:8b"
        />
        <TextField
          label="Base URL"
          hint="An OpenAI-compatible endpoint, for example https://api.openai.com/v1 or http://localhost:11434/v1"
          value={baseUrl}
          onChange={(event) => {
            setBaseUrl(event.target.value);
          }}
          required
          maxLength={512}
        />
        <TextField
          label="API key"
          type="password"
          autoComplete="off"
          hint={
            initial === undefined
              ? 'Stored encrypted; only its last four characters are ever shown again.'
              : `Leave blank to keep the stored key (…${initial.api_key_hint || 'none'}).`
          }
          value={apiKey}
          onChange={(event) => {
            setApiKey(event.target.value);
          }}
          maxLength={512}
        />
        <TextField
          label="Max output tokens"
          type="number"
          min={64}
          max={32000}
          value={maxTokens}
          onChange={(event) => {
            setMaxTokens(event.target.value);
          }}
          required
        />
        <TextField
          label="Temperature"
          type="number"
          min={0}
          max={2}
          step={0.1}
          value={temperature}
          onChange={(event) => {
            setTemperature(event.target.value);
          }}
          required
        />
      </div>
      <fieldset className="flex flex-wrap gap-4 text-sm">
        <legend className="mb-1 text-sm font-medium text-text">Roles</legend>
        {LLM_ROLES.map((role) => (
          <label key={role} className="flex items-center gap-2 text-text">
            <input
              type="checkbox"
              checked={roles.includes(role)}
              onChange={() => {
                toggleRole(role);
              }}
            />
            {ROLE_LABELS[role]}
          </label>
        ))}
        <label className="flex items-center gap-2 text-text">
          <input
            type="checkbox"
            checked={enabled}
            onChange={(event) => {
              setEnabled(event.target.checked);
            }}
          />
          Enabled
        </label>
      </fieldset>
      {error === null ? null : <Alert tone="error">{error}</Alert>}
      <div className="flex gap-2">
        <Button type="submit" busy={busy} disabled={roles.length === 0}>
          {initial === undefined ? 'Create profile' : 'Save changes'}
        </Button>
        <Button variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
      </div>
    </form>
  );
}

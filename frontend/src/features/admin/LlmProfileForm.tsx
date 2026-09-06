import { useEffect, useRef, useState } from 'react';
import type { SyntheticEvent } from 'react';

import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SelectField, TextField } from '@/components/ui/Field';
import type { LlmProfile, LlmProfileInput } from '@/lib/api/llm';

import { LUNA_MODEL, OPENAI_BASE_URL, TEXT_ROLES } from './llmPresentation';

export interface LlmProfileFormProps {
  initial?: LlmProfile | undefined;
  replacement?: boolean;
  models?: readonly string[];
  busy: boolean;
  error: string | null;
  onSubmit: (input: LlmProfileInput) => void;
  onCancel: () => void;
}

/** Keys exist only in this mounted form and are sent to the server once on save. */
export function LlmProfileForm({
  initial,
  replacement = false,
  models = [],
  busy,
  error,
  onSubmit,
  onCancel,
}: LlmProfileFormProps) {
  const form = useRef<HTMLFormElement>(null);
  useEffect(() => {
    form.current?.querySelector('select')?.focus();
  }, []);
  const [provider, setProvider] = useState(
    initial === undefined || initial.base_url === OPENAI_BASE_URL ? 'openai' : 'custom',
  );
  const [name, setName] = useState(
    initial === undefined ? 'OpenAI Luna' : `${initial.name}${replacement ? ' replacement' : ''}`,
  );
  const [baseUrl, setBaseUrl] = useState(initial?.base_url ?? OPENAI_BASE_URL);
  const [model, setModel] = useState(initial?.model ?? LUNA_MODEL);
  const [apiKey, setApiKey] = useState('');
  const [embeddings, setEmbeddings] = useState(initial?.roles.includes('embeddings') ?? false);
  const [embeddingEnabled, setEmbeddingEnabled] = useState(initial?.enabled ?? false);
  const [maxTokens, setMaxTokens] = useState(String(initial?.max_output_tokens ?? 16_000));
  const [temperature, setTemperature] = useState(String(initial?.temperature ?? 0.2));
  const [effort, setEffort] = useState<NonNullable<LlmProfile['reasoning_effort']> | ''>(
    initial?.reasoning_effort ?? (initial === undefined ? 'max' : ''),
  );
  const sameCredentials =
    initial !== undefined &&
    !replacement &&
    apiKey === '' &&
    baseUrl.trim().replace(/\/$/, '') === initial.base_url.replace(/\/$/, '');

  const submit = (event: SyntheticEvent<HTMLFormElement>) => {
    event.preventDefault();
    const input: LlmProfileInput = {
      name: name.trim(),
      base_url: baseUrl.trim(),
      model: model.trim(),
      roles: embeddings ? ['embeddings'] : [...TEXT_ROLES],
      max_output_tokens: Number(maxTokens),
      temperature: Number(temperature),
      reasoning_effort: embeddings || effort === '' ? null : effort,
      enabled: embeddings && embeddingEnabled,
    };
    if (apiKey.trim()) input.api_key = apiKey.trim();
    onSubmit(input);
  };

  const selectProvider = (value: string) => {
    setProvider(value);
    setApiKey('');
    if (value === 'openai') {
      setBaseUrl(OPENAI_BASE_URL);
      setModel(LUNA_MODEL);
      setEffort('max');
      setMaxTokens('16000');
    } else {
      setBaseUrl('');
      setModel('');
      setEffort('');
    }
  };

  return (
    <form
      ref={form}
      onSubmit={submit}
      aria-label={
        initial === undefined || replacement ? 'New AI connection' : `Edit ${initial.name}`
      }
      className="space-y-5 border-t border-line pt-5"
    >
      <div>
        <h2 className="text-base font-semibold">
          {initial === undefined || replacement
            ? 'Configure a connection'
            : 'Edit draft connection'}
        </h2>
        <p className="mt-1 text-sm text-muted">
          Save a draft, test the model, then choose where to apply it.
        </p>
      </div>
      <fieldset disabled={busy} className="space-y-5">
        <div className="grid gap-4 md:grid-cols-2">
          <SelectField
            label="Provider"
            value={provider}
            onChange={(event) => selectProvider(event.target.value)}
            options={[
              { value: 'openai', label: 'OpenAI' },
              { value: 'custom', label: 'Custom OpenAI-compatible' },
            ]}
          />
          <TextField
            label="Connection name"
            value={name}
            onChange={(event) => setName(event.target.value)}
            required
            maxLength={80}
          />
          <TextField
            label="Base URL"
            value={baseUrl}
            onChange={(event) => {
              setBaseUrl(event.target.value);
              setApiKey('');
            }}
            readOnly={provider === 'openai'}
            required
            maxLength={512}
            hint={
              provider === 'openai'
                ? 'Official OpenAI API endpoint.'
                : 'The endpoint receiving prompts and evidence. For example, http://localhost:11434/v1.'
            }
          />
          <TextField
            label="API key"
            type="password"
            autoComplete="new-password"
            spellCheck={false}
            value={apiKey}
            onChange={(event) => setApiKey(event.target.value)}
            maxLength={512}
            required={provider === 'openai' && (initial === undefined || replacement)}
            hint={
              initial === undefined || replacement
                ? 'Stored encrypted on the server. Only its ending is shown later.'
                : `Leave blank to keep the stored key (…${initial.api_key_hint || 'none'}).`
            }
          />
        </div>
        {models.length > 0 && sameCredentials && (
          <SelectField
            label="Models returned by this account"
            value={models.includes(model) ? model : ''}
            onChange={(event) => {
              if (event.target.value) setModel(event.target.value);
            }}
            options={[
              { value: '', label: 'Enter a model ID below' },
              ...models.map((value) => ({ value, label: value })),
            ]}
            hint="Availability and compatibility are checked when you test the saved draft."
          />
        )}
        <div className="grid gap-4 md:grid-cols-2">
          <TextField
            label="Model ID"
            value={model}
            onChange={(event) => setModel(event.target.value)}
            required
            maxLength={120}
            hint="Enter a model ID manually, or load this account’s models after saving the draft."
          />
          {!embeddings && (
            <SelectField
              label="Reasoning effort"
              value={effort}
              onChange={(event) => setEffort(event.target.value as typeof effort)}
              options={[
                { value: '', label: 'Provider default' },
                { value: 'none', label: 'None' },
                { value: 'minimal', label: 'Minimal' },
                { value: 'low', label: 'Low' },
                { value: 'medium', label: 'Medium' },
                { value: 'high', label: 'High' },
                { value: 'xhigh', label: 'Extra high' },
                { value: 'max', label: 'Max' },
              ]}
              hint={
                effort === 'max'
                  ? 'More reasoning; may take longer and use more tokens.'
                  : 'Only select an effort supported by the chosen model.'
              }
            />
          )}
        </div>
        <details className="border-t border-line pt-4">
          <summary className="cursor-pointer text-sm font-medium">Advanced settings</summary>
          <div className="mt-4 space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <TextField
                label="Response budget (includes reasoning)"
                type="number"
                min={64}
                max={32000}
                value={maxTokens}
                onChange={(event) => setMaxTokens(event.target.value)}
                required
              />
              <TextField
                label="Temperature"
                type="number"
                min={0}
                max={2}
                step={0.1}
                value={temperature}
                onChange={(event) => setTemperature(event.target.value)}
                required
                hint="Some reasoning models use their own temperature setting."
              />
            </div>
            <label className="flex items-start gap-2 text-sm">
              <input
                type="checkbox"
                checked={embeddings}
                onChange={(event) => {
                  setEmbeddings(event.target.checked);
                  if (event.target.checked) setEffort('');
                }}
                className="mt-1"
              />
              Use this connection for embeddings only
            </label>
            <p className="text-xs text-muted">
              Embeddings power report search and remain separate from the text model used for
              direction, assessment, challenge and translation.
            </p>
            {embeddings && (
              <label className="flex items-start gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={embeddingEnabled}
                  onChange={(event) => setEmbeddingEnabled(event.target.checked)}
                  className="mt-1"
                />
                Enable this embeddings connection when saved
              </label>
            )}
          </div>
        </details>
      </fieldset>
      {error !== null && <Alert tone="error">{error}</Alert>}
      <div className="flex flex-wrap gap-2">
        <Button type="submit" busy={busy}>
          Save draft
        </Button>
        <Button variant="ghost" disabled={busy} onClick={onCancel}>
          Cancel
        </Button>
      </div>
    </form>
  );
}

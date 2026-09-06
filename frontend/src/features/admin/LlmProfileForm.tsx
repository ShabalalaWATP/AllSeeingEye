import { useEffect, useRef, useState } from 'react';
import type { SyntheticEvent } from 'react';

import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SelectField, TextField } from '@/components/ui/Field';
import type { LlmProfile, LlmProfileInput } from '@/lib/api/llm';

import { LlmAdvancedSettings } from './LlmAdvancedSettings';
import { BedrockRegion, bedrockEndpoint, regionFromEndpoint } from './BedrockRegion';
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
    initial?.provider === 'bedrock'
      ? 'bedrock'
      : initial === undefined || initial.base_url === OPENAI_BASE_URL
        ? 'openai'
        : 'custom',
  );
  const [name, setName] = useState(
    initial === undefined ? 'OpenAI Luna' : `${initial.name}${replacement ? ' replacement' : ''}`,
  );
  const [region, setRegion] = useState(
    initial?.provider === 'bedrock' ? regionFromEndpoint(initial.base_url) : '',
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
    initial.provider === (provider === 'bedrock' ? 'bedrock' : 'openai_compatible') &&
    apiKey === '' &&
    baseUrl.trim().replace(/\/$/, '') === initial.base_url.replace(/\/$/, '');

  const submit = (event: SyntheticEvent<HTMLFormElement>) => {
    event.preventDefault();
    const input: LlmProfileInput = {
      provider: provider === 'bedrock' ? 'bedrock' : 'openai_compatible',
      name: name.trim(),
      base_url: baseUrl.trim(),
      model: model.trim(),
      roles: provider !== 'bedrock' && embeddings ? ['embeddings'] : [...TEXT_ROLES],
      max_output_tokens: Number(maxTokens),
      temperature: Number(temperature),
      reasoning_effort: provider === 'bedrock' || embeddings || effort === '' ? null : effort,
      enabled: provider !== 'bedrock' && embeddings && embeddingEnabled,
    };
    if (apiKey.trim()) input.api_key = apiKey.trim();
    onSubmit(input);
  };

  const selectProvider = (value: string) => {
    setProvider(value);
    setApiKey('');
    setEmbeddings(false);
    setEmbeddingEnabled(false);
    if (value === 'bedrock') setTemperature(String(Math.min(Number(temperature) || 0, 1)));
    setName(
      value === 'openai'
        ? 'OpenAI Luna'
        : value === 'bedrock'
          ? 'Amazon Bedrock'
          : 'Custom connection',
    );
    if (value === 'openai') {
      setBaseUrl(OPENAI_BASE_URL);
      setModel(LUNA_MODEL);
      setEffort('max');
      setMaxTokens('16000');
    } else {
      setRegion('');
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
              { value: 'bedrock', label: 'Amazon Bedrock' },
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
          {provider === 'bedrock' && (
            <BedrockRegion
              value={region}
              onChange={(value) => {
                setRegion(value);
                setBaseUrl(bedrockEndpoint(value));
                setApiKey('');
              }}
            />
          )}
          <TextField
            label="Base URL"
            value={baseUrl}
            onChange={(event) => {
              setBaseUrl(event.target.value);
              setApiKey('');
            }}
            readOnly={provider !== 'custom'}
            required
            maxLength={512}
            hint={
              provider === 'openai'
                ? 'Official OpenAI API endpoint.'
                : provider === 'bedrock'
                  ? 'AWS Bedrock Converse endpoint for the selected region.'
                  : 'The endpoint receiving prompts and evidence. For example, http://localhost:11434/v1.'
            }
          />
          <TextField
            label={provider === 'bedrock' ? 'Bedrock API key' : 'API key'}
            type="password"
            autoComplete="new-password"
            spellCheck={false}
            value={apiKey}
            onChange={(event) => setApiKey(event.target.value)}
            maxLength={16384}
            required={provider !== 'custom' && !sameCredentials}
            hint={
              !sameCredentials
                ? provider === 'bedrock'
                  ? 'Use a Bedrock API key, not an IAM access key. Stored encrypted on the server. Short-term keys expire and are not renewed automatically.'
                  : 'Stored encrypted on the server. Only its ending is shown later.'
                : `Leave blank to keep the stored key (…${initial.api_key_hint || 'none'}).`
            }
          />
        </div>
        {provider !== 'bedrock' && models.length > 0 && sameCredentials && (
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
            label={provider === 'bedrock' ? 'Model or inference profile ID' : 'Model ID'}
            value={model}
            onChange={(event) => setModel(event.target.value)}
            required
            maxLength={provider === 'bedrock' ? 2048 : 120}
            placeholder={provider === 'bedrock' ? 'e.g. openai.gpt-oss-120b-1:0' : undefined}
            hint={
              provider === 'bedrock'
                ? 'Copy a Converse-compatible model or inference profile ID from the AWS console for this region. Test connection checks access and structured-output compatibility.'
                : 'Enter a model ID manually, or load this account’s models after saving the draft.'
            }
          />
          {provider === 'bedrock' ? (
            <p className="self-end pb-2 text-xs leading-5 text-muted">
              Reasoning uses the provider default. This connection supports text requests only; IAM
              roles and model catalogue discovery are not supported.
            </p>
          ) : (
            !embeddings && (
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
            )
          )}
        </div>
        <LlmAdvancedSettings
          bedrock={provider === 'bedrock'}
          maxTokens={maxTokens}
          setMaxTokens={setMaxTokens}
          temperature={temperature}
          setTemperature={setTemperature}
          embeddings={embeddings}
          setEmbeddings={(value) => {
            setEmbeddings(value);
            if (value) setEffort('');
          }}
          embeddingEnabled={embeddingEnabled}
          setEmbeddingEnabled={setEmbeddingEnabled}
        />
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

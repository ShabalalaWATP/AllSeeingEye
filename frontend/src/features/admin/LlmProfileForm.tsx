import { useEffect, useRef, useState } from 'react';
import type { SyntheticEvent } from 'react';

import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SelectField, TextField } from '@/components/ui/Field';
import type { LlmProfile, LlmProfileInput } from '@/lib/api/llm';

import { LlmModelSelection } from './LlmModelSelection';
import { useLlmModelDiscovery } from './useLlmModelDiscovery';
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
  onTest?: (input: LlmProfileInput) => void;
  onChange?: () => void;
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
  onTest,
  onChange,
}: LlmProfileFormProps) {
  const [step, setStep] = useState(1);
  const guided = !!onTest;
  const [originalCatalogue] = useState({ id: initial?.id, revision: initial?.revision });
  const form = useRef<HTMLFormElement>(null);
  useEffect(() => {
    form.current
      ?.querySelector<HTMLInputElement | HTMLSelectElement>(
        step === 2 ? 'input[name="model"]' : 'select',
      )
      ?.focus();
  }, [step]);
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

  const discovery = useLlmModelDiscovery(
    baseUrl,
    apiKey,
    sameCredentials ? initial.id : undefined,
    provider !== 'bedrock' && (provider === 'custom' || !!apiKey.trim() || sameCredentials),
  );
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
    setApiKey('');
    if ((event.nativeEvent as SubmitEvent).submitter?.getAttribute('value') === 'test' && onTest)
      onTest(input);
    else onSubmit(input);
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
      onChange={onChange}
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
          Connect your provider, test the chosen model, then confirm who will use it.
        </p>
      </div>
      <fieldset disabled={busy} className="space-y-5">
        {guided && step === 2 && (
          <div className="space-y-2">
            <p className="text-sm">
              <strong>{name}</strong> - {baseUrl}
            </p>
            <Button
              variant="ghost"
              onClick={() => {
                setStep(1);
                onChange?.();
              }}
            >
              Back to provider
            </Button>
          </div>
        )}
        <div hidden={guided && step !== 1}>
          <h3 className="text-sm font-semibold">1. Connect your provider</h3>
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
              onBlur={() => {
                if (!guided && provider === 'custom') void discovery.load();
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
              onBlur={() => {
                if (!guided) void discovery.load();
              }}
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
        </div>
        {guided && step === 1 && (
          <Button
            onClick={() => {
              if (!form.current?.reportValidity()) return;
              setStep(2);
              void discovery.load();
            }}
          >
            Continue to model
          </Button>
        )}
        {(!guided || step === 2) && (
          <>
            <LlmModelSelection
              bedrock={provider === 'bedrock'}
              models={
                discovery.loaded
                  ? discovery.models
                  : sameCredentials &&
                      initial.id === originalCatalogue.id &&
                      initial.revision === originalCatalogue.revision
                    ? models
                    : []
              }
              model={model}
              setModel={(value) => {
                setModel(value);
                if (value === LUNA_MODEL && effort === 'minimal') setEffort('max');
              }}
              effort={effort}
              setEffort={setEffort}
              embeddings={embeddings}
              discovery={discovery}
              onDiscover={() => void discovery.load()}
              canDiscover={provider === 'custom' || !!apiKey.trim() || sameCredentials}
              canTest={!!onTest && !embeddings}
            />
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
          </>
        )}
      </fieldset>
      {error !== null && <Alert tone="error">{error}</Alert>}
      <div className="flex flex-wrap gap-2">
        {(!guided || step === 2) && (
          <Button type="submit" busy={busy}>
            Save draft
          </Button>
        )}
        <Button variant="ghost" disabled={busy} onClick={onCancel}>
          Cancel
        </Button>
      </div>
    </form>
  );
}

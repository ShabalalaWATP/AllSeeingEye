import { useEffect, useRef, useState } from 'react';
import type { SyntheticEvent } from 'react';

import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import type { LlmProfile, LlmProfileInput } from '@/lib/api/llm';

import { LlmModelSelection } from './LlmModelSelection';
import { useLlmModelDiscovery } from './useLlmModelDiscovery';
import { LlmAdvancedSettings } from './LlmAdvancedSettings';
import { bedrockEndpoint, regionFromEndpoint } from './BedrockRegion';
import { OPENAI_BASE_URL, TEXT_ROLES } from './llmPresentation';
import { LlmProviderFields } from './LlmProviderFields';

function availableName(preferred: string, names: readonly string[]) {
  let candidate = preferred.slice(0, 74);
  let suffix = 2;
  while (names.includes(candidate)) candidate = `${preferred.slice(0, 74)} ${suffix++}`;
  return candidate;
}

export interface LlmProfileFormProps {
  embeddingsOnly?: boolean;
  initial?: LlmProfile | undefined;
  models?: readonly string[];
  names?: readonly string[];
  busy: boolean;
  error: string | null;
  onSubmit: ((input: LlmProfileInput) => void) | ((input: LlmProfileInput) => Promise<boolean>);
  onCancel: () => void;
}

/** Keys stay in component memory until a save succeeds, so failed saves remain retryable. */
export function LlmProfileForm({
  embeddingsOnly = false,
  initial,
  models = [],
  names = [],
  busy,
  error,
  onSubmit,
  onCancel,
}: LlmProfileFormProps) {
  const [originalCatalogue] = useState({ id: initial?.id, revision: initial?.revision });
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
  const [name, setName] = useState(initial?.name ?? availableName('OpenAI connection', names));
  const customName = useRef(initial !== undefined);
  const [region, setRegion] = useState(
    initial?.provider === 'bedrock' ? regionFromEndpoint(initial.base_url) : '',
  );
  const [baseUrl, setBaseUrl] = useState(initial?.base_url ?? OPENAI_BASE_URL);
  const [model, setModel] = useState(initial?.model ?? '');
  const [apiKey, setApiKey] = useState('');
  const [embeddings, setEmbeddings] = useState(
    initial?.roles.includes('embeddings') ?? embeddingsOnly,
  );
  const [embeddingEnabled, setEmbeddingEnabled] = useState(initial?.enabled ?? false);
  const [maxTokens, setMaxTokens] = useState(String(initial?.max_output_tokens ?? 16_000));
  const [temperature, setTemperature] = useState(String(initial?.temperature ?? 0.2));
  const [effort, setEffort] = useState<NonNullable<LlmProfile['reasoning_effort']> | ''>(
    initial?.reasoning_effort ?? '',
  );
  const sameCredentials =
    initial?.provider === (provider === 'bedrock' ? 'bedrock' : 'openai_compatible') &&
    apiKey === '' &&
    baseUrl.trim().replace(/\/$/, '') === initial.base_url.replace(/\/$/, '');

  const discovery = useLlmModelDiscovery(
    baseUrl,
    apiKey,
    sameCredentials ? initial.id : undefined,
    provider !== 'bedrock' && (provider === 'custom' || !!apiKey.trim() || sameCredentials),
  );
  const submit = async (event: SyntheticEvent<HTMLFormElement>) => {
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
    const saved = await onSubmit(input);
    if (saved === true) setApiKey('');
  };

  const selectProvider = (value: string) => {
    setProvider(value);
    setApiKey('');
    setEmbeddings(false);
    setEmbeddingEnabled(false);
    if (value === 'bedrock') setTemperature(String(Math.min(Number(temperature) || 0, 1)));
    if (!customName.current)
      setName(
        availableName(
          value === 'openai'
            ? 'OpenAI connection'
            : value === 'bedrock'
              ? 'Amazon Bedrock'
              : 'Custom connection',
          names,
        ),
      );
    setModel('');
    setEffort('');
    if (value === 'openai') {
      setBaseUrl(OPENAI_BASE_URL);
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
      onSubmit={(event) => void submit(event)}
      aria-label={initial === undefined ? 'New AI connection' : `Edit ${initial.name}`}
      className="space-y-6"
    >
      <div>
        <h2 className="text-lg font-semibold">Edit draft connection</h2>
        <p className="mt-1 text-sm text-muted">
          Add your credentials, then choose a model available to your account.
        </p>
      </div>
      <fieldset disabled={busy} className="space-y-5">
        <div>
          <LlmProviderFields
            provider={provider}
            setProvider={selectProvider}
            name={name}
            setName={(value) => {
              customName.current = true;
              setName(value);
            }}
            region={region}
            setRegion={(value) => {
              setRegion(value);
              setBaseUrl(bedrockEndpoint(value));
              setApiKey('');
            }}
            baseUrl={baseUrl}
            setBaseUrl={(value) => {
              setBaseUrl(value);
              setApiKey('');
            }}
            apiKey={apiKey}
            setApiKey={setApiKey}
            sameCredentials={sameCredentials}
            {...(initial ? { keyHint: initial.api_key_hint } : {})}
            discover={() => void discovery.load()}
          />
        </div>
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
            if (value !== model) setEffort('');
            if (!customName.current) setName(availableName(value || 'OpenAI connection', names));
          }}
          effort={effort}
          setEffort={setEffort}
          embeddings={embeddings}
          discovery={discovery}
          onDiscover={() => void discovery.load()}
          canDiscover={provider === 'custom' || !!apiKey.trim() || sameCredentials}
        />
        <LlmAdvancedSettings
          bedrock={provider === 'bedrock'}
          maxTokens={maxTokens}
          setMaxTokens={(value) => {
            setMaxTokens(value);
          }}
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
      <div className="flex flex-wrap items-center gap-2 border-t border-line pt-4">
        <Button type="submit" busy={busy} disabled={!model.trim()}>
          Save draft
        </Button>
        <Button variant="ghost" disabled={busy} onClick={onCancel}>
          Cancel
        </Button>
      </div>
    </form>
  );
}

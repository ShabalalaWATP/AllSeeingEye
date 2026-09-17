import { SelectField, TextField } from '@/components/ui/Field';
import { BedrockRegion, bedrockEndpoint } from './BedrockRegion';
import { OPENAI_BASE_URL } from './llmPresentation';
import type { ModelSetupState } from './ModelSetupState';

export function ModelSetupName({
  state,
  duplicate,
}: {
  state: ModelSetupState;
  duplicate: boolean;
}) {
  const { fields, change } = state;
  return (
    <div className="space-y-5">
      <TextField
        label="Connection name"
        name="connection-name"
        required
        maxLength={80}
        value={fields.name}
        placeholder="For example, OpenAI Luna"
        onChange={(event) => change({ name: event.target.value })}
        error={duplicate ? 'This name is already used. Choose another name.' : undefined}
        hint="Give this model connection a name you will recognise."
      />
      <details className="border-t border-line pt-4" open={fields.provider !== 'openai'}>
        <summary className="cursor-pointer text-sm text-muted">
          Provider:{' '}
          {fields.provider === 'openai'
            ? 'OpenAI'
            : fields.provider === 'bedrock'
              ? 'Amazon Bedrock'
              : 'Custom endpoint'}
        </summary>
        <div className="mt-4 space-y-4">
          <SelectField
            label="Provider"
            value={fields.provider}
            onChange={(event) => {
              const provider = event.target.value as typeof fields.provider;
              change({
                provider,
                baseUrl: provider === 'openai' ? OPENAI_BASE_URL : '',
                region: '',
                apiKey: '',
                model: '',
                effort: '',
              });
            }}
            options={[
              { value: 'openai', label: 'OpenAI' },
              { value: 'bedrock', label: 'Amazon Bedrock' },
              { value: 'custom', label: 'Custom OpenAI-compatible' },
            ]}
          />
          {fields.provider === 'bedrock' && (
            <BedrockRegion
              value={fields.region}
              onChange={(region) =>
                change({ region, baseUrl: bedrockEndpoint(region), apiKey: '' })
              }
            />
          )}
          <TextField
            label="API endpoint"
            value={fields.baseUrl}
            readOnly={fields.provider !== 'custom'}
            required
            maxLength={512}
            onChange={(event) => change({ baseUrl: event.target.value, apiKey: '' })}
            hint={
              fields.provider === 'openai'
                ? 'The official endpoint is already configured.'
                : 'This is where research prompts and evidence will be sent.'
            }
          />
        </div>
      </details>
    </div>
  );
}

export function ModelSetupKey({ state }: { state: ModelSetupState }) {
  return (
    <TextField
      label={state.fields.provider === 'bedrock' ? 'Bedrock API key' : 'API key'}
      type="password"
      autoComplete="new-password"
      spellCheck={false}
      maxLength={16384}
      required={state.fields.provider !== 'custom' && !state.storedKey}
      value={state.fields.apiKey}
      onChange={(event) => state.change({ apiKey: event.target.value })}
      hint={
        state.storedKey
          ? `Leave blank to reuse the encrypted key ending ${state.draft?.api_key_hint ?? 'unknown'}.`
          : state.fields.provider === 'bedrock'
            ? 'Use a Bedrock API key, not an IAM access key. Short-term keys need renewing.'
            : 'Stored encrypted on the server. It is used to load your available models.'
      }
    />
  );
}

export function ModelSetupReasoning({ state }: { state: ModelSetupState }) {
  if (state.fields.provider === 'bedrock')
    return (
      <p className="text-sm leading-6 text-muted">
        Amazon Bedrock uses the selected model’s default reasoning settings. Continue to test
        compatibility.
      </p>
    );
  return (
    <SelectField
      label="Reasoning level"
      value={state.fields.effort}
      onChange={(event) =>
        state.change({ effort: event.target.value as typeof state.fields.effort })
      }
      options={[
        { value: '', label: 'Provider default' },
        ...['none', 'minimal', 'low', 'medium', 'high', 'xhigh', 'max'].map((value) => ({
          value,
          label: value === 'xhigh' ? 'Extra high' : value.charAt(0).toUpperCase() + value.slice(1),
        })),
      ]}
      hint="Provider default is the safest starting point. Higher reasoning can cost more and take longer. The next step tests this exact choice."
    />
  );
}

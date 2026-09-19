import { SelectField, TextField } from '@/components/ui/Field';
import { BedrockRegion } from './BedrockRegion';

export function LlmProviderFields({
  provider,
  setProvider,
  name,
  setName,
  region,
  setRegion,
  baseUrl,
  setBaseUrl,
  apiKey,
  setApiKey,
  sameCredentials,
  keyHint,
  discover,
}: {
  provider: string;
  setProvider: (value: string) => void;
  name: string;
  setName: (value: string) => void;
  region: string;
  setRegion: (value: string) => void;
  baseUrl: string;
  setBaseUrl: (value: string) => void;
  apiKey: string;
  setApiKey: (value: string) => void;
  sameCredentials: boolean;
  keyHint?: string;
  discover: () => void;
}) {
  return (
    <div className="space-y-5">
      <div className="grid gap-4 sm:grid-cols-2">
        <SelectField
          label="Provider"
          value={provider}
          onChange={(event) => setProvider(event.target.value)}
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
          hint="A name to recognise this connection later."
        />
      </div>
      {provider === 'bedrock' && <BedrockRegion value={region} onChange={setRegion} />}
      <TextField
        label="Base URL"
        value={baseUrl}
        onChange={(event) => setBaseUrl(event.target.value)}
        onBlur={provider === 'custom' ? discover : undefined}
        readOnly={provider !== 'custom'}
        required
        maxLength={512}
        hint={
          provider === 'openai'
            ? 'Official OpenAI API endpoint, already configured.'
            : provider === 'bedrock'
              ? 'AWS Bedrock Converse endpoint for the selected region.'
              : 'The endpoint receiving prompts and evidence, for example http://localhost:11434/v1.'
        }
      />
      <TextField
        label={provider === 'bedrock' ? 'Bedrock API key' : 'API key'}
        type="password"
        autoComplete="new-password"
        spellCheck={false}
        onBlur={discover}
        value={apiKey}
        onChange={(event) => setApiKey(event.target.value)}
        maxLength={16384}
        required={provider !== 'custom' && !sameCredentials}
        hint={
          sameCredentials
            ? `Leave blank to keep the stored key (…${keyHint ?? 'none'}).`
            : provider === 'bedrock'
              ? 'Use a Bedrock API key, not an IAM access key. Stored encrypted. Short-term keys need renewing.'
              : 'Stored encrypted on the server. Your key is never shown to other users.'
        }
      />
    </div>
  );
}

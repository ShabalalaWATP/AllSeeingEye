import { useId } from 'react';

import { TextField } from '@/components/ui/Field';

const REGION = /^[a-z]{2}(?:-[a-z]+){1,2}-[0-9]+$/;

export function bedrockEndpoint(region: string): string {
  return REGION.test(region) ? `https://bedrock-runtime.${region}.amazonaws.com` : '';
}

export function regionFromEndpoint(endpoint: string): string {
  return /^https:\/\/bedrock-runtime\.([a-z0-9-]+)\.amazonaws\.com\/?$/.exec(endpoint)?.[1] ?? '';
}

export function BedrockRegion({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  const listId = useId();
  return (
    <div>
      <TextField
        label="AWS region"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        list={listId}
        placeholder="Choose or enter a region"
        required
        pattern="[a-z]{2}(?:-[a-z]+){1,2}-[0-9]+"
        maxLength={40}
        autoComplete="off"
        spellCheck={false}
        hint="Choose the region where your AWS account has model access, for example us-east-1."
      />
      <datalist id={listId}>
        {[
          'us-east-1',
          'us-east-2',
          'us-west-2',
          'eu-west-1',
          'eu-west-2',
          'eu-central-1',
          'ap-southeast-1',
          'ap-southeast-2',
          'ap-northeast-1',
        ].map((region) => (
          <option key={region} value={region} />
        ))}
      </datalist>
    </div>
  );
}

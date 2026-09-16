/** The model a previewed person or team would use. Configuration only, never a credential. */
import type { AiEffectiveModel as Model } from '@/lib/api/aiUsage';

const ROUTING: Record<string, string> = {
  personal: 'Personal override',
  team: 'Team override',
  global: 'Global connection',
  legacy: 'First enabled profile (no connection assigned)',
};

export function AiEffectiveModel({ model }: { model: Model | null | undefined }) {
  if (!model) return null;
  if (model.unavailable) {
    return (
      <p className="text-sm text-amber" role="status">
        <span className="font-medium">Model:</span> {model.unavailable}
      </p>
    );
  }
  const capped =
    model.mechanical_effort !== null && model.mechanical_effort !== model.reasoning_effort;
  return (
    <div className="text-sm">
      <p>
        <span className="font-medium">Model:</span>{' '}
        <span className="font-mono">{model.model}</span>
        {model.profile_name ? <span className="text-muted"> · {model.profile_name}</span> : null}
        <span className="text-muted"> · {ROUTING[model.policy ?? ''] ?? model.policy}</span>
      </p>
      <p className="text-xs text-muted">
        Reasoning effort {model.reasoning_effort ?? 'provider default'}
        {capped ? `, lowered to ${model.mechanical_effort} for mechanical work` : ''}.
      </p>
    </div>
  );
}

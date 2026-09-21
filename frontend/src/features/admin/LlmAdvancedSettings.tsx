import { TextField } from '@/components/ui/Field';

export function LlmAdvancedSettings({
  embeddingsOnly = false,
  bedrock,
  maxTokens,
  setMaxTokens,
  temperature,
  setTemperature,
  embeddings,
  setEmbeddings,
  embeddingEnabled,
  setEmbeddingEnabled,
}: {
  embeddingsOnly?: boolean;
  bedrock: boolean;
  maxTokens: string;
  setMaxTokens: (value: string) => void;
  temperature: string;
  setTemperature: (value: string) => void;
  embeddings: boolean;
  setEmbeddings: (value: boolean) => void;
  embeddingEnabled: boolean;
  setEmbeddingEnabled: (value: boolean) => void;
}) {
  return (
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
            max={bedrock ? 1 : 2}
            step={0.1}
            value={temperature}
            onChange={(event) => setTemperature(event.target.value)}
            required
            hint="Some reasoning models use their own temperature setting."
          />
        </div>
        {!bedrock && (
          <>
            <label className="flex items-start gap-2 text-sm">
              <input
                type="checkbox"
                checked={embeddings}
                disabled={embeddingsOnly}
                onChange={(event) => setEmbeddings(event.target.checked)}
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
          </>
        )}
      </div>
    </details>
  );
}

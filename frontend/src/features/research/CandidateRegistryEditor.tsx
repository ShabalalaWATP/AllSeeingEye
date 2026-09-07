import { Button } from '@/components/ui/Button';
import { TextField } from '@/components/ui/Field';
import { registryLabels, registryNamespaceSchema } from '@/lib/api/registryRouting';
import type { CandidateHypothesis } from '@/lib/api/researchPlan';

export function CandidateRegistryEditor({
  candidate,
  index,
  update,
}: {
  candidate: CandidateHypothesis;
  index: number;
  update: (change: Partial<CandidateHypothesis>) => void;
}) {
  const identifiers = candidate.registry_identifiers ?? [];
  return (
    <section className="space-y-3" aria-label={`Candidate ${index + 1} registry identifiers`}>
      <p className="text-xs text-muted">
        Choose a registry explicitly for an exact lookup. Names and untyped identifiers remain
        context only. Preview after editing to check provider, country and date support.
      </p>
      {identifiers.map((identifier, position) => {
        const prefix = `Candidate ${index + 1} registry identifier ${position + 1}`;
        return (
          <fieldset key={identifier.id} className="space-y-2 rounded border border-line p-3">
            <legend className="text-xs">Registry identifier {position + 1}</legend>
            <label className="block text-sm">
              {prefix} type
              <select
                className="mt-1 block w-full rounded border border-line bg-ground p-2"
                value={identifier.namespace}
                onChange={(event) =>
                  update({
                    registry_identifiers: identifiers.map((row) =>
                      row.id === identifier.id
                        ? { ...row, namespace: registryNamespaceSchema.parse(event.target.value) }
                        : row,
                    ),
                  })
                }
              >
                {Object.entries(registryLabels).map(([key, label]) => (
                  <option key={key} value={key}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <TextField
              label={`${prefix} value`}
              value={identifier.value}
              maxLength={300}
              hint="Original text is retained. The server validates and canonicalises the identifier."
              onChange={(event) =>
                update({
                  registry_identifiers: identifiers.map((row) =>
                    row.id === identifier.id ? { ...row, value: event.target.value } : row,
                  ),
                })
              }
            />
            <Button
              variant="ghost"
              onClick={() =>
                update({
                  registry_identifiers: identifiers.filter((row) => row.id !== identifier.id),
                })
              }
            >
              Remove registry identifier {position + 1}
            </Button>
          </fieldset>
        );
      })}
      <Button
        variant="secondary"
        disabled={identifiers.length + (candidate.identifiers?.length ?? 0) >= 8}
        onClick={() =>
          update({
            registry_identifiers: [
              ...identifiers,
              { id: crypto.randomUUID(), namespace: 'lei', value: '' },
            ],
          })
        }
      >
        Add registry identifier
      </Button>
    </section>
  );
}

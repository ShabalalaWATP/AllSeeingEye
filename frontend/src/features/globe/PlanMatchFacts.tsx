import { usePlanMapFilterStore } from '@/stores/planMapFilter';

/** Every SIR of the selected map plan that this event satisfies, from the latest sample. */
export function PlanMatchFacts({ eventId }: { eventId: string }) {
  const codes = usePlanMapFilterStore((state) => state.codes?.get(eventId));
  const result = usePlanMapFilterStore((state) => state.result);
  if (codes === undefined || result === null) return null;
  const texts = new Map(
    result.plan.pirs.flatMap((pir) => pir.sirs.map((sir) => [sir.code, sir.text])),
  );
  return (
    <section aria-label="Plan matches" className="mt-3 text-xs">
      <p className="text-muted">Matches {result.plan.name}</p>
      <ul className="mt-1 space-y-1">
        {codes.map((code) => (
          <li key={code}>
            <span className="mr-2 font-mono text-text">{code}</span>
            <span className="text-muted">
              {texts.get(code) ?? 'Requirement no longer in the plan'}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}

import type { RfResultExplanation } from '@/lib/map/rfResultExplanation';

const colours = {
  pass: 'text-cyan',
  caution: 'text-amber-200',
  blocked: 'text-red-300',
  unknown: 'text-muted',
  scenario: 'text-indigo-200',
};

/** A common reading order across models, without turning an estimate into a promise. */
export function RfResultSummary({ value }: { value: RfResultExplanation }) {
  return (
    <section aria-label="Result explained" className="rf-result-summary space-y-3">
      <p className="rf-result-kicker text-xs uppercase tracking-wider text-muted">Your result</p>
      <h3 className={`text-lg font-medium ${colours[value.tone]}`}>{value.headline}</h3>
      <p className="text-sm leading-relaxed">{value.explanation}</p>
      <div className="rf-result-next-step space-y-1">
        <h4 className="text-sm font-medium">What to try next</h4>
        <p className="text-sm leading-relaxed">{value.nextStep}</p>
      </div>
      <div className="space-y-1 text-sm leading-relaxed">
        <h4 className="font-medium">Limits of this estimate</h4>
        <p className="text-muted">{value.limitations}</p>
      </div>
      <p className="text-xs text-muted">This is a planning estimate, not a reception test.</p>
    </section>
  );
}

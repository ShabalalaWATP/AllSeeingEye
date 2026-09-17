const STEPS = ['Provider', 'Model & test', 'Audience & apply'];

/** Persistent orientation without allowing an untested draft to skip ahead. */
export function LlmSetupProgress({ step }: { step: number }) {
  return (
    <ol
      aria-label="Connection setup progress"
      className="grid grid-cols-3 gap-3 border-b border-line pb-5"
    >
      {STEPS.map((label, index) => (
        <li
          key={label}
          aria-current={step === index + 1 ? 'step' : undefined}
          className={`flex items-center gap-2 text-xs sm:text-sm ${step === index + 1 ? 'font-medium text-text' : 'text-muted'}`}
        >
          <span
            aria-hidden="true"
            className={`flex size-6 shrink-0 items-center justify-center rounded-full border text-xs transition-colors motion-reduce:transition-none ${step >= index + 1 ? 'border-ember bg-ember/10 text-ember' : 'border-line'}`}
          >
            {step > index + 1 ? '✓' : index + 1}
          </span>
          {label}
        </li>
      ))}
    </ol>
  );
}

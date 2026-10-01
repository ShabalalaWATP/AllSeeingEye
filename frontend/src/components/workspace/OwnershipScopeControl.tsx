import type { OwnershipScopeState } from '@/lib/hooks/useOwnershipScope';
import type { OwnershipScope } from '@/lib/ownershipScope';

const OPTIONS: readonly { value: OwnershipScope; label: string }[] = [
  { value: 'mine', label: 'Mine and my teams' },
  { value: 'all', label: 'All users' },
];

const pill =
  'min-h-10 rounded-md px-3 text-sm transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ember';

/** The sentence describing which records a scoped list holds. */
export function scopeCaption(scope: OwnershipScope, noun: string): string {
  return scope === 'all'
    ? `Showing every user's personal ${noun} and every team's ${noun}. Acting on another person's record changes it for them too.`
    : `Showing your personal ${noun} and ${noun} from your current teams.`;
}

/**
 * Administrators choose between their own work and every user's; other roles see only the
 * caption. Native toggle buttons keep the choice keyboard-operable and announced.
 */
export function OwnershipScopeControl({
  state,
  noun,
}: {
  state: OwnershipScopeState;
  /** Plural, lower case: "alerts" or "research runs". */
  noun: string;
}) {
  return (
    <div className="flex flex-col gap-2">
      {state.isAdmin && (
        <div
          role="group"
          aria-label={`Whose ${noun} to show`}
          className="flex w-fit flex-wrap gap-1 rounded-lg bg-surface p-1"
        >
          {OPTIONS.map((option) => (
            <button
              key={option.value}
              type="button"
              aria-pressed={state.scope === option.value}
              onClick={() => state.setScope(option.value)}
              className={`${pill} ${
                state.scope === option.value
                  ? 'bg-ember font-semibold text-ground'
                  : 'text-muted hover:bg-surface-2 hover:text-text'
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
      )}
      <p className="text-xs leading-5 text-muted">{scopeCaption(state.scope, noun)}</p>
    </div>
  );
}

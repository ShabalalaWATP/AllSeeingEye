import { useId } from 'react';

import { Button } from '@/components/ui/Button';
import { usePreferencesStore } from '@/stores/preferences';

/** Keyboard preferences apply at once and are kept in this browser only. */
export function KeyboardPreferences() {
  const id = useId();
  const singleKey = usePreferencesStore((state) => state.singleKeyShortcuts);
  const setSingleKey = usePreferencesStore((state) => state.setSingleKeyShortcuts);
  const openHelp = usePreferencesStore((state) => state.openShortcutHelp);
  return (
    <section aria-labelledby={`${id}-title`} className="space-y-7">
      <header>
        <h2 id={`${id}-title`} className="text-xl font-semibold">
          Keyboard
        </h2>
        <p className="mt-2 text-sm text-muted">
          How the workspace responds to the keyboard. Changes apply straight away and are saved in
          this browser.
        </p>
      </header>
      <div className="flex items-start gap-3 border-y border-line py-5">
        <input
          id={id}
          aria-describedby={`${id}-help`}
          type="checkbox"
          checked={singleKey}
          onChange={(event) => setSingleKey(event.target.checked)}
          className="mt-1 size-4 shrink-0 accent-ember"
        />
        <div>
          <label htmlFor={id} className="block cursor-pointer text-sm font-medium">
            Single-key shortcuts
          </label>
          <p id={`${id}-help`} className="mt-1 text-sm text-muted">
            Press G, M, O, [ or ? on their own to change the view, open the ops room, fold the
            navigation or list every shortcut. Turn this off if you use speech input or stray key
            presses move you around. Ctrl K search and Esc always work.
          </p>
        </div>
      </div>
      <div>
        <Button variant="secondary" onClick={openHelp}>
          Show keyboard shortcuts
        </Button>
      </div>
    </section>
  );
}

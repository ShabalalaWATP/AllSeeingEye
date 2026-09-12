import { useId, useRef, useState } from 'react';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import type { Profile, ProfileInput } from '@/lib/api/profile';
import { useProfile } from '@/stores/profile';

const themes = [
  {
    value: 'obsidian',
    label: 'Obsidian',
    detail: 'Near-black with warm accents',
    ground: '#07070b',
    surface: '#1c1c26',
    accent: '#ff6f37',
    text: '#e9e4dc',
  },
  {
    value: 'slate',
    label: 'Slate',
    detail: 'Deep slate with cool accents',
    ground: '#0b1420',
    surface: '#1b2d40',
    accent: '#72dcec',
    text: '#edf5fa',
  },
  {
    value: 'light',
    label: 'Daylight',
    detail: 'Light surfaces and clear contrast',
    ground: '#f5f6f8',
    surface: '#e7ebef',
    accent: '#a63d13',
    text: '#17212d',
  },
] as const;

export function AppearancePreferences() {
  const state = useProfile();
  if (!state.profile)
    return state.loading ? (
      <LoadingNote label="Loading your appearance…" />
    ) : (
      <div className="space-y-4">
        <Alert tone="error">{state.error ?? 'Your preferences could not be loaded.'}</Alert>
        <Button onClick={() => void state.reload()}>Try again</Button>
      </div>
    );
  return <AppearanceForm profile={state.profile} save={state.save} error={state.error} />;
}

function AppearanceForm({
  profile,
  save,
  error,
}: {
  profile: Profile;
  save: (input: ProfileInput) => Promise<Profile | null>;
  error: string | null;
}) {
  const motionId = useId();
  const [theme, setTheme] = useState(profile.appearance_theme);
  const [reduced, setReduced] = useState(profile.reduced_motion);
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const inFlight = useRef(false);
  const dirty = theme !== profile.appearance_theme || reduced !== profile.reduced_motion;
  const submit = async () => {
    if (inFlight.current || !dirty) return;
    inFlight.current = true;
    setBusy(true);
    setSaved(false);
    const result = await save({ appearance_theme: theme, reduced_motion: reduced });
    if (result) {
      setTheme(result.appearance_theme);
      setReduced(result.reduced_motion);
      setSaved(true);
    }
    inFlight.current = false;
    setBusy(false);
  };
  return (
    <form
      aria-label="Appearance preferences"
      onSubmit={(event) => {
        event.preventDefault();
        void submit();
      }}
      className="space-y-7"
    >
      <header>
        <h2 className="text-xl font-semibold">Appearance</h2>
        <p className="mt-2 text-sm text-muted">
          Your workspace colours and movement, saved to your account.
        </p>
      </header>
      <fieldset disabled={busy}>
        <legend className="mb-3 text-sm font-medium">Colour theme</legend>
        <div className="grid grid-cols-3 gap-2 sm:gap-3">
          {themes.map((option) => (
            <label
              key={option.value}
              className={`cursor-pointer rounded-lg border p-2 transition-colors sm:p-3 ${theme === option.value ? 'border-ember bg-surface-2' : 'border-line hover:border-muted'}`}
            >
              <span
                aria-hidden="true"
                className="mb-3 flex h-16 gap-2 overflow-hidden rounded-md border border-line p-2 sm:h-24"
                style={{ background: option.ground }}
              >
                <span className="w-5 rounded-sm" style={{ background: option.surface }} />
                <span className="flex flex-1 flex-col gap-2 pt-1">
                  <span className="h-1.5 w-3/5 rounded" style={{ background: option.text }} />
                  <span
                    className="h-1 w-4/5 rounded opacity-50"
                    style={{ background: option.text }}
                  />
                  <span
                    className="mt-auto h-7 rounded-sm border-l-2"
                    style={{ background: option.surface, borderColor: option.accent }}
                  />
                </span>
              </span>
              <span className="flex items-center gap-1 text-xs font-medium sm:gap-2 sm:text-sm">
                <input
                  type="radio"
                  name="appearance-theme"
                  value={option.value}
                  checked={theme === option.value}
                  onChange={() => {
                    setTheme(option.value);
                    setSaved(false);
                  }}
                  className="size-4 accent-ember"
                />
                {option.label}
              </span>
              <span className="mt-1 hidden text-xs text-muted sm:block">{option.detail}</span>
            </label>
          ))}
        </div>
      </fieldset>
      <fieldset disabled={busy} className="border-y border-line py-5">
        <div className="flex items-start gap-3">
          <input
            id={motionId}
            aria-describedby={`${motionId}-help`}
            type="checkbox"
            checked={reduced}
            onChange={(event) => {
              setReduced(event.target.checked);
              setSaved(false);
            }}
            className="mt-1 size-4 shrink-0 accent-ember"
          />
          <div>
            <label htmlFor={motionId} className="block cursor-pointer text-sm font-medium">
              Reduce motion
            </label>
            <p id={`${motionId}-help`} className="mt-1 text-sm text-muted">
              Keep the eye still and reduce interface animation and automatic globe rotation. Your
              device’s reduced-motion setting is always respected.
            </p>
          </div>
        </div>
      </fieldset>
      {error && <Alert tone="error">{error}</Alert>}
      {saved && <Alert tone="success">Your appearance has been saved.</Alert>}
      <div className="flex items-center gap-3">
        <Button type="submit" busy={busy} disabled={!dirty}>
          Save appearance
        </Button>
        <Button
          variant="ghost"
          disabled={busy || !dirty}
          onClick={() => {
            setTheme(profile.appearance_theme);
            setReduced(profile.reduced_motion);
            setSaved(false);
          }}
        >
          Reset changes
        </Button>
      </div>
    </form>
  );
}

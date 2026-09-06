import { useRef, useState } from 'react';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import type { Profile, ProfileInput } from '@/lib/api/profile';
import { useAuthStore } from '@/stores/auth';
import { useProfile } from '@/stores/profile';

import { PreferenceFields } from './PreferenceFields';
import type { EditableSection } from './PreferenceFields';

const content = {
  profile: {
    title: 'Personal details',
    description: 'Choose how your name and dates appear in the app.',
  },
  research: {
    title: 'Research defaults',
    description: 'Start new research with these settings. Adjust them for each question.',
  },
  reports: {
    title: 'Report preferences',
    description: 'Set the language, style and export format for your reports.',
  },
};

export function ProfilePreferences({ section }: { section: EditableSection }) {
  const state = useProfile();
  if (state.loading && !state.profile) return <LoadingNote label="Loading your preferences…" />;
  if (!state.profile)
    return (
      <div className="space-y-4">
        <Alert tone="error">{state.error ?? 'Your preferences could not be loaded.'}</Alert>
        <Button onClick={() => void state.reload()}>Try again</Button>
      </div>
    );
  return (
    <PreferencesForm
      section={section}
      profile={state.profile}
      save={state.save}
      error={state.error}
    />
  );
}

function sectionInput(section: EditableSection, profile: Profile): ProfileInput {
  if (section === 'profile')
    return {
      display_name: profile.display_name.trim(),
      timezone: profile.timezone,
      date_format: profile.date_format,
    };
  if (section === 'research')
    return {
      research_mode: profile.research_mode,
      research_country: profile.research_country,
      research_languages: profile.research_languages,
      research_window_days: profile.research_window_days,
    };
  return {
    report_language: profile.report_language,
    report_style: profile.report_style,
    export_format: profile.export_format,
  };
}

function PreferencesForm({
  section,
  profile,
  save,
  error,
}: {
  section: EditableSection;
  profile: Profile;
  error: string | null;
  save: (input: ProfileInput) => Promise<Profile | null>;
}) {
  const actor = useAuthStore((state) => state.user);
  const [draft, setDraft] = useState(profile);
  const [sourceLanguages, setSourceLanguages] = useState(profile.research_languages.join(', '));
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const [validation, setValidation] = useState<string | null>(null);
  const inFlight = useRef(false);
  const dirty =
    JSON.stringify(sectionInput(section, draft)) !==
      JSON.stringify(sectionInput(section, profile)) ||
    (section === 'research' && sourceLanguages !== profile.research_languages.join(', '));
  const edit = <K extends keyof Profile>(key: K, value: Profile[K]) => {
    setDraft((current) => ({ ...current, [key]: value }));
    setSaved(false);
    setValidation(null);
  };
  const reset = () => {
    setDraft(profile);
    setSourceLanguages(profile.research_languages.join(', '));
    setSaved(false);
    setValidation(null);
  };
  const submit = async () => {
    if (inFlight.current) return;
    if (!draft.display_name.trim()) {
      setValidation('Enter a display name.');
      return;
    }
    const codes = [...new Set(sourceLanguages.split(',').map((code) => code.trim()))];
    if (
      section === 'research' &&
      (codes.length > 8 || codes.some((code) => !/^[a-z]{2,3}(?:-[A-Za-z]{2,4})?$/.test(code)))
    ) {
      setValidation('Choose between one and eight source languages.');
      return;
    }
    inFlight.current = true;
    setBusy(true);
    setSaved(false);
    const result = await save(sectionInput(section, { ...draft, research_languages: codes }));
    if (result) {
      setDraft(result);
      setSourceLanguages(result.research_languages.join(', '));
      setSaved(true);
    }
    inFlight.current = false;
    setBusy(false);
  };
  return (
    <form
      aria-label={content[section].title}
      onSubmit={(event) => {
        event.preventDefault();
        void submit();
      }}
      className="flex max-w-xl flex-col gap-6"
    >
      <header>
        <h2 className="text-xl font-semibold">{content[section].title}</h2>
        <p className="mt-2 text-sm text-muted">{content[section].description}</p>
      </header>
      {section === 'profile' && (
        <dl className="grid gap-4 border-y border-line py-4 sm:grid-cols-2">
          <div>
            <dt className="text-xs text-muted">Email address</dt>
            <dd className="mt-1 break-all text-sm">{actor?.email}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted">Account role</dt>
            <dd className="mt-1 text-sm capitalize">{actor?.role}</dd>
          </div>
        </dl>
      )}
      <fieldset disabled={busy} className="flex flex-col gap-5">
        <PreferenceFields
          section={section}
          draft={draft}
          onChange={edit}
          sourceLanguages={sourceLanguages}
          onLanguagesChange={(value) => {
            setSourceLanguages(value);
            setSaved(false);
            setValidation(null);
          }}
        />
      </fieldset>
      {validation || error ? <Alert tone="error">{validation ?? error}</Alert> : null}
      {saved && <Alert tone="success">Your preferences have been saved.</Alert>}
      <div className="flex items-center gap-3 border-t border-line pt-5">
        <Button type="submit" busy={busy} disabled={!dirty}>
          {busy ? 'Saving…' : 'Save changes'}
        </Button>
        <Button variant="ghost" disabled={busy || !dirty} onClick={reset}>
          Reset changes
        </Button>
        {dirty && !busy && <span className="ml-auto text-xs text-muted">Unsaved changes</span>}
      </div>
    </form>
  );
}

import { useEffect, useState } from 'react';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SelectField, TextAreaField, TextField } from '@/components/ui/Field';
import { asApiError, describeError } from '@/lib/api/errors';
import {
  getDirectoryProfile,
  updateDirectoryProfile,
  type DirectoryProfile as DirectoryProfileData,
} from '@/lib/api/directoryProfile';

const timezones = () => ['UTC', ...Intl.supportedValuesOf('timeZone')];

function splitList(value: string): string[] {
  return [
    ...new Set(
      value
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean),
    ),
  ];
}

export function DirectoryProfile() {
  const [profile, setProfile] = useState<DirectoryProfileData | null>(null);
  const [draft, setDraft] = useState<DirectoryProfileData | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const value = await getDirectoryProfile();
      setProfile(value);
      setDraft(value);
    } catch (caught) {
      setError(describeError(asApiError(caught)));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    // The request updates this component when it resolves; it is intentionally
    // started after the first render so loading feedback is visible.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, []);

  if (loading && draft === null) return <LoadingNote label="Loading directory profile" />;
  if (draft === null || profile === null) {
    return (
      <div className="flex flex-col gap-4">
        <Alert tone="error">{error ?? 'Directory profile unavailable.'}</Alert>
        <Button onClick={() => void load()}>Try again</Button>
      </div>
    );
  }
  const currentDraft = draft;
  const currentProfile = profile;

  const edit = <K extends keyof DirectoryProfileData>(key: K, value: DirectoryProfileData[K]) => {
    setDraft((current) => (current ? { ...current, [key]: value } : current));
    setSaved(false);
    setError(null);
  };
  const dirty = JSON.stringify(currentDraft) !== JSON.stringify(currentProfile);

  async function submit() {
    if (busy || !dirty) return;
    setBusy(true);
    setError(null);
    setSaved(false);
    try {
      const optionalText = (value: string | null): string | null => {
        const cleaned = value?.trim() ?? '';
        return cleaned === '' ? null : cleaned;
      };
      const updated = await updateDirectoryProfile({
        username: optionalText(currentDraft.username)?.toLowerCase() ?? null,
        job_title: optionalText(currentDraft.job_title),
        organisation: optionalText(currentDraft.organisation),
        biography: optionalText(currentDraft.biography),
        country: optionalText(currentDraft.country)?.toUpperCase() ?? null,
        languages: splitList(currentDraft.languages.join(', ')),
        expertise: splitList(currentDraft.expertise.join(', ')),
        timezone: currentDraft.timezone ?? null,
        is_discoverable: currentDraft.is_discoverable,
        show_timezone: currentDraft.show_timezone,
        expected_revision: currentProfile.revision,
      });
      setProfile(updated);
      setDraft(updated);
      setSaved(true);
    } catch (caught) {
      setError(describeError(asApiError(caught)));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form
      aria-label="Directory profile"
      className="flex max-w-2xl flex-col gap-6"
      onSubmit={(event) => {
        event.preventDefault();
        void submit();
      }}
    >
      <header>
        <p className="font-mono text-xs uppercase tracking-widest text-cyan">Optional discovery</p>
        <h2 className="mt-2 text-xl font-semibold">Directory profile</h2>
        <p className="mt-2 text-sm leading-6 text-muted">
          Share a small professional profile with teammates and authorised operators. Your login
          email, MFA state and private activity never appear in directory search.
        </p>
      </header>
      <fieldset disabled={busy} className="flex flex-col gap-5">
        <TextField
          label="Username"
          hint="A unique handle, 3 to 32 lowercase letters, numbers or underscores."
          value={currentDraft.username ?? ''}
          maxLength={32}
          onChange={(event) => edit('username', event.target.value)}
        />
        <div className="grid gap-5 sm:grid-cols-2">
          <TextField
            label="Job title"
            maxLength={120}
            value={currentDraft.job_title ?? ''}
            onChange={(event) => edit('job_title', event.target.value)}
          />
          <TextField
            label="Organisation"
            maxLength={120}
            value={currentDraft.organisation ?? ''}
            onChange={(event) => edit('organisation', event.target.value)}
          />
          <TextField
            label="Country code"
            hint="Two-letter ISO code, for example GB."
            maxLength={2}
            value={currentDraft.country ?? ''}
            onChange={(event) => edit('country', event.target.value)}
          />
          <SelectField
            label="Timezone"
            value={currentDraft.timezone ?? 'UTC'}
            options={timezones().map((zone) => ({ value: zone, label: zone.replaceAll('_', ' ') }))}
            onChange={(event) => edit('timezone', event.target.value)}
          />
        </div>
        <TextAreaField
          label="Biography"
          maxLength={500}
          value={currentDraft.biography ?? ''}
          onChange={(event) => edit('biography', event.target.value)}
        />
        <TextField
          label="Languages"
          hint="Comma-separated ISO language codes, up to eight."
          value={currentDraft.languages.join(', ')}
          onChange={(event) => edit('languages', splitList(event.target.value))}
        />
        <TextField
          label="Expertise"
          hint="Comma-separated topics, up to ten."
          value={currentDraft.expertise.join(', ')}
          onChange={(event) => edit('expertise', splitList(event.target.value))}
        />
        <div className="flex items-start gap-3 text-sm">
          <input
            id="directory-discoverable"
            type="checkbox"
            className="mt-1 size-4 accent-cyan"
            checked={currentDraft.is_discoverable}
            onChange={(event) => edit('is_discoverable', event.target.checked)}
          />
          <div>
            <label htmlFor="directory-discoverable" className="font-medium">
              Show me in directory search
            </label>
            <p className="mt-1 text-xs text-muted">
              Only authenticated users can search, and only this profile is returned.
            </p>
          </div>
        </div>
        <div className="flex items-start gap-3 text-sm">
          <input
            id="directory-show-timezone"
            type="checkbox"
            className="mt-1 size-4 accent-cyan"
            checked={currentDraft.show_timezone}
            onChange={(event) => edit('show_timezone', event.target.checked)}
          />
          <div>
            <label htmlFor="directory-show-timezone" className="font-medium">
              Show my timezone
            </label>
            <p className="mt-1 text-xs text-muted">
              Useful for handovers. It stays private until you enable this.
            </p>
          </div>
        </div>
      </fieldset>
      {error ? <Alert tone="error">{error}</Alert> : null}
      {saved ? <Alert tone="success">Directory profile saved.</Alert> : null}
      <div className="flex items-center gap-3 border-t border-line pt-5">
        <Button type="submit" busy={busy} disabled={!dirty}>
          {busy ? 'Saving…' : 'Save directory profile'}
        </Button>
        <Button variant="ghost" disabled={busy || !dirty} onClick={() => setDraft(currentProfile)}>
          Reset
        </Button>
      </div>
    </form>
  );
}

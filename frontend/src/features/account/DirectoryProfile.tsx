import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SelectField, TextAreaField, TextField } from '@/components/ui/Field';
import { DIRECTORY_FIELDS, type DirectoryField } from '@/lib/api/directoryProfile';
import { useAuthStore } from '@/stores/auth';

import { DirectoryAvatarEditor } from './DirectoryAvatarEditor';
import { useDirectoryProfileEditor } from './useDirectoryProfileEditor';

const timezones = () => ['UTC', ...Intl.supportedValuesOf('timeZone')];

const fieldLabels: Record<DirectoryField, string> = {
  job_title: 'Job title',
  organisation: 'Organisation',
  biography: 'Biography',
  country: 'Country',
  languages: 'Languages',
  expertise: 'Expertise',
  timezone: 'Timezone',
};

export function DirectoryProfile() {
  const editor = useDirectoryProfileEditor();
  const { profile, draft, loading, busy, error, saved, dirty, load, edit, submit, avatarChanged } =
    editor;
  const displayName = useAuthStore((state) => state.user?.display_name ?? 'You');

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

  const toggleField = (field: DirectoryField, shown: boolean) => {
    const selected = new Set(currentDraft.visible_fields);
    if (shown) selected.add(field);
    else selected.delete(field);
    edit(
      'visible_fields',
      DIRECTORY_FIELDS.filter((item) => selected.has(item)),
    );
  };
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
      <DirectoryAvatarEditor
        profile={currentProfile}
        name={displayName}
        disabled={busy || editor.latest !== null || editor.needsReload}
        onChange={avatarChanged}
      />
      <fieldset
        disabled={busy || editor.latest !== null || editor.needsReload}
        className="flex flex-col gap-5"
      >
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
          value={currentDraft.languages}
          onChange={(event) => edit('languages', event.target.value)}
        />
        <TextField
          label="Expertise"
          hint="Comma-separated topics, up to ten."
          value={currentDraft.expertise}
          onChange={(event) => edit('expertise', event.target.value)}
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
        <fieldset className="flex flex-col gap-2">
          <legend className="text-sm font-medium">Show in directory results</legend>
          <p className="text-xs text-muted">
            Choose which filled-in fields other people see. Timezone stays private unless you tick
            it. Teammates always see your display name and avatar.
          </p>
          <div className="mt-1 grid gap-2 sm:grid-cols-2">
            {DIRECTORY_FIELDS.map((field) => (
              <label key={field} className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  className="size-4 accent-cyan"
                  checked={currentDraft.visible_fields.includes(field)}
                  onChange={(event) => toggleField(field, event.target.checked)}
                />
                {fieldLabels[field]}
              </label>
            ))}
          </div>
        </fieldset>
      </fieldset>
      {error ? <Alert tone="error">{error}</Alert> : null}
      {editor.latest && (
        <Alert tone="warning">
          <p>
            Your profile changed elsewhere. Your unsaved edits are kept. Keeping your edits replaces
            the latest values only in fields you edited; other fields use the latest profile. Review
            the result before saving.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <Button disabled={busy} onClick={() => editor.resolveConflict(true)}>
              Keep my edits over latest profile
            </Button>
            <Button disabled={busy} variant="ghost" onClick={() => editor.resolveConflict(false)}>
              Discard my edits and use latest profile
            </Button>
          </div>
        </Alert>
      )}
      {editor.needsReload && (
        <Button busy={busy} onClick={() => void editor.reloadLatest()}>
          Retry loading latest profile
        </Button>
      )}
      {saved ? <Alert tone="success">Directory profile saved.</Alert> : null}
      <div className="flex items-center gap-3 border-t border-line pt-5">
        <Button
          type="submit"
          busy={busy}
          disabled={!dirty || editor.latest !== null || editor.needsReload}
        >
          {busy ? 'Saving…' : 'Save directory profile'}
        </Button>
        <Button
          variant="ghost"
          disabled={busy || !dirty || editor.latest !== null || editor.needsReload}
          onClick={editor.reset}
        >
          Reset
        </Button>
      </div>
    </form>
  );
}

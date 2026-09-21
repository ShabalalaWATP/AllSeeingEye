import type { DirectoryProfile, DirectoryProfileChanges } from '@/lib/api/directoryProfile';

/** Keep list text intact during editing. Parsing belongs at the save boundary. */
export type DirectoryDraft = Omit<DirectoryProfile, 'languages' | 'expertise'> & {
  languages: string;
  expertise: string;
};

export function directoryDraft(profile: DirectoryProfile): DirectoryDraft {
  return {
    ...profile,
    languages: profile.languages.join(', '),
    expertise: profile.expertise.join(', '),
  };
}

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

function optionalText(value: string | null): string | null {
  const cleaned = value?.trim() ?? '';
  return cleaned === '' ? null : cleaned;
}

export function directoryChanges(draft: DirectoryDraft, revision: number): DirectoryProfileChanges {
  return {
    username: optionalText(draft.username)?.toLowerCase() ?? null,
    job_title: optionalText(draft.job_title),
    organisation: optionalText(draft.organisation),
    biography: optionalText(draft.biography),
    country: optionalText(draft.country)?.toUpperCase() ?? null,
    languages: splitList(draft.languages),
    expertise: splitList(draft.expertise),
    timezone: draft.timezone,
    is_discoverable: draft.is_discoverable,
    visible_fields: draft.visible_fields,
    expected_revision: revision,
  };
}

const editableFields = [
  'username',
  'job_title',
  'organisation',
  'biography',
  'country',
  'languages',
  'expertise',
  'timezone',
  'is_discoverable',
  'visible_fields',
] as const;

/** Only explicit local edits replace latest values, never stale untouched fields or metadata. */
export function reapplyDirectoryDraft(
  baseline: DirectoryProfile,
  draft: DirectoryDraft,
  latest: DirectoryProfile,
): DirectoryDraft {
  const before = directoryDraft(baseline);
  const merged = directoryDraft(latest);
  for (const key of editableFields) {
    if (JSON.stringify(draft[key]) !== JSON.stringify(before[key])) {
      Object.assign(merged, { [key]: draft[key] });
    }
  }
  return merged;
}

import type { ResearchGeolocation } from '@/lib/api/researchGeolocation';
import type { ResearchInputReceipt } from '@/lib/api/researchInputs';
import type { Workspaces } from '@/lib/hooks/useWorkspaces';

import { plainUser } from './fixtures';

export const photoId = '10000000-0000-4000-8000-000000000001';
export const derivedPhotoId = '10000000-0000-4000-8000-000000000002';
export const photoTeamId = '10000000-0000-4000-8000-000000000003';

export function photoReceipt(overrides: Partial<ResearchInputReceipt> = {}): ResearchInputReceipt {
  return {
    id: photoId,
    parent_input_id: null,
    filename: 'landmark.jpg',
    media_type: 'image/jpeg',
    sha256: 'a'.repeat(64),
    imported_at: new Date().toISOString(),
    expires_at: new Date(Date.now() + 900_000).toISOString(),
    event_count: 1,
    extracted_characters: 30,
    preview: 'A sign reads station.',
    limitations: ['Image metadata is not proof of location.'],
    previews: [{ seconds: 0, sha256: 'b'.repeat(64), png_base64: 'iVBORw0KGgo=' }],
    ...overrides,
  };
}

export function photoAssessment(overrides: Partial<ResearchGeolocation> = {}): ResearchGeolocation {
  return {
    input: photoReceipt({ id: derivedPhotoId, parent_input_id: photoId }),
    candidate_status: 'unverified',
    status: 'candidates',
    summary: 'A landmark suggests London, but the facade needs comparison.',
    visual_clues: ['A tall clock tower beside a river.'],
    candidates: [
      {
        label: 'Westminster, London',
        country_iso: 'GB',
        precision: 'landmark',
        supporting_clues: ['The tower shape resembles the Elizabeth Tower.'],
        contradictions: ['The photograph does not show the full facade.'],
        coordinates: {
          latitude: 51.5,
          longitude: -0.12,
          uncertainty_radius_km: 1,
          basis: 'Approximate landmark position, inferred from visual clues.',
        },
      },
    ],
    verification_steps: ['Compare the facade with independent street-level photographs.'],
    limitations: ['This is an unverified visual hypothesis.'],
    provenance: {
      profile_id: '10000000-0000-4000-8000-000000000004',
      profile_revision: 1,
      provider: 'openai_compatible',
      configured_model: 'configured-vision-model',
      returned_model: 'returned-vision-model',
      analysed_at: new Date().toISOString(),
      original_sha256: 'a'.repeat(64),
      image_sha256: 'b'.repeat(64),
    },
    ...overrides,
  };
}

export function photoWorkspaces(): Workspaces {
  return {
    key: 'photo-test-workspaces',
    data: null,
    loading: false,
    error: null,
    teams: [
      {
        team: {
          id: photoTeamId,
          name: 'Regional research',
          is_active: true,
          created_by: plainUser.id,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          description: null,
        },
        members: [],
      },
    ],
    label: (id) => (id ? 'Team: Regional research' : 'Personal'),
    canManage: () => true,
    canAcknowledge: () => true,
    reload: () => Promise.resolve(),
    refresh: () => Promise.resolve(),
    setData: () => undefined,
  };
}

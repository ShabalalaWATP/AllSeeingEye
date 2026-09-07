import { describe, expect, it } from 'vitest';
import { projectSchema } from './projects';
import { evidenceItemSchema } from './reports';

const project = {
  dataset_id: 'aiddata-geogcdf',
  release_id: 'v3.0.1',
  project_id: '35756',
  source_sha256: 'a'.repeat(64),
  recipient_iso3: 'LAO',
  reported_status: 'Completion',
  precision: 'precise',
  attribution: 'AidData; OpenStreetMap contributors',
  data_licence: 'ODC-By-1.0',
  geometry_licence: 'ODbL-1.0',
  limitations: 'Historical reported status; derived geometry.',
  commitment_year: 2011,
  implementation_year: null,
  completion_year: 2012,
};

describe('project evidence metadata', () => {
  it('uses Unicode code points for limits and rejects lone surrogates', () => {
    expect(projectSchema.parse({ ...project, project_id: '𠮷'.repeat(120) }).project_id).toBe(
      '𠮷'.repeat(120),
    );
    expect(projectSchema.safeParse({ ...project, project_id: '𠮷'.repeat(121) }).success).toBe(
      false,
    );
    expect(projectSchema.safeParse({ ...project, project_id: '\uD800' }).success).toBe(false);
  });
  it('preserves year precision through the evidence response parser', () => {
    const parsed = evidenceItemSchema.parse({
      label: 'E1',
      event_id: 'event',
      source_id: 'aiddata',
      source_name: 'AidData',
      category: 'economic',
      title: 'Project',
      summary: null,
      url: null,
      archive_url: null,
      published_at: null,
      grade: 'F6',
      grade_rationale: '',
      country_iso: 'LA',
      flags: [],
      project,
    });
    expect(parsed.project).toEqual(project);
    expect(parsed.published_at).toBeNull();
  });

  it.each([true, '2020', 2020.5, 0, 9999])('rejects invalid year %s', (year) => {
    expect(projectSchema.safeParse({ ...project, commitment_year: year }).success).toBe(false);
  });
});

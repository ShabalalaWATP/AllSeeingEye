import { describe, expect, it } from 'vitest';

import { APP_TITLE, documentTitle, pageTitle } from './pageTitles';

describe('page titles', () => {
  it.each([
    ['/', 'Map'],
    ['/watches', 'Watches'],
    ['/warning', 'Alerts'],
    ['/direction', 'Plans and areas'],
    ['/direction/plans/b2b2', 'Collection plan'],
    ['/annotation-monitors', 'Annotation monitors'],
    ['/annotation-monitors/monitor-1', 'Annotation monitor'],
    ['/annotation-monitors/monitor-1/transitions/t-1', 'Annotation change'],
    ['/research', 'Research'],
    ['/research/', 'Research'],
    ['/research/saved', 'Saved research'],
    ['/research/jobs', 'Research progress'],
    ['/research/jobs/job-1', 'Research job'],
    ['/subscriptions/saved', 'Saved updates'],
    ['/geolocation/saved', 'Saved assessments'],
    ['/reports/11111111', 'Report'],
    ['/trackers', 'Live monitor'],
    ['/trackers/maritime', 'Maritime'],
    ['/trackers/conflicts/ukraine', 'Conflict'],
    ['/trackers/disasters/flood', 'Disaster'],
    ['/conflicts/ukraine', 'Ukraine war'],
    ['/cyber', 'Cyber intelligence'],
    ['/account', 'Account'],
    ['/account/security', 'Account security'],
    ['/settings', 'Your settings'],
    ['/admin', 'Administration'],
    ['/admin/users', 'Users · Administration'],
    ['/admin/nowhere', 'Administration'],
    ['/elsewhere', APP_TITLE],
  ])('names %s as %s', (path, title) => {
    expect(pageTitle(path)).toBe(title);
  });

  it('prefixes the application name only for known pages', () => {
    expect(documentTitle('/watches')).toBe('Watches · The All Seeing Eye');
    expect(documentTitle('/elsewhere')).toBe('The All Seeing Eye');
  });
});

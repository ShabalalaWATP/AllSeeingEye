import { act } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';
import { plainUser, tokenFor } from '@/test/fixtures';

import {
  plainText,
  prepareReportWatch,
  readReportWatchDraft,
  reportWatchScope,
} from './alertRuleDraft';
import { prepareAreaWatch, readAreaWatchDraft } from './areaWatchDraft';

const source = {
  reportId: 'r1',
  version: 2,
  title: 'Title',
  judgementNumber: 1,
  statement: 'Statement',
  teamId: null,
};
const input = { source, countries: [], categories: [], geometry: null, areaNote: null };

describe('report watch drafts', () => {
  it('keeps indicator wording as plain one-line text without shortening it', () => {
    expect(plainText(' Troops\u0000 massing\n\tnear   <b>Kharkiv</b> ')).toBe(
      'Troops massing near <b>Kharkiv</b>',
    );
    useAuthStore.getState().setSession(tokenFor(plainUser));
    const long = 'x'.repeat(200);
    const draft = prepareReportWatch({ ...input, indicators: [long, long, ' ', 'Second'] });
    expect(draft.indicators).toEqual([long, 'Second']);
  });

  it('refuses unidentifiable versions and empty indicators, and needs a signed-in actor', () => {
    useAuthStore.getState().setSession(tokenFor(plainUser));
    expect(() =>
      prepareReportWatch({ ...input, source: { ...source, version: 0 }, indicators: ['a'] }),
    ).toThrow('This report version cannot be identified.');
    expect(() => prepareReportWatch({ ...input, indicators: ['  '] })).toThrow(
      'This judgement has no indicators to watch for.',
    );
    useAuthStore.getState().clearSession();
    expect(() => prepareReportWatch({ ...input, indicators: ['a'] })).toThrow(
      'Sign in before preparing an alert rule.',
    );
  });

  it('gives way to a newer area hand-off and is dropped on an access change', () => {
    useAuthStore.getState().setSession(tokenFor(plainUser));
    prepareReportWatch({ ...input, indicators: ['a'] });
    act(() =>
      prepareAreaWatch({ source: 'viewport', bounds: { west: 0, south: 0, east: 1, north: 1 } }),
    );
    expect(readReportWatchDraft()).toBeNull();
    prepareReportWatch({ ...input, indicators: ['a'] });
    expect(readAreaWatchDraft()).toBeNull();
    act(() => invalidateWorkspaceAccess());
    expect(readReportWatchDraft()).toBeNull();
  });

  it('carries only explicit, well-formed report scope', () => {
    const area = { geometry: { type: 'FeatureCollection', features: [] }, sha256: 'a'.repeat(64) };
    expect(reportWatchScope({ country: 'UA', categories: ['conflict', 'bogus'] })).toEqual({
      countries: ['UA'],
      categories: ['conflict'],
      geometry: null,
      areaNote: null,
    });
    expect(reportWatchScope({ research_area: area, map_origin: { area } })).toMatchObject({
      geometry: null,
      areaNote:
        "The report's saved area could not be carried over. Choose a location for the alert rule.",
    });
    expect(reportWatchScope({ map_origin: { area } }).geometry).toEqual(area.geometry);
    expect(reportWatchScope({ countries: ['UA', 'Ukraine'] })).toMatchObject({
      countries: [],
      areaNote:
        "The report's saved countries could not be carried over. Choose them for the alert rule.",
    });
  });
});

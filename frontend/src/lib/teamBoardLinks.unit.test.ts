import { describe, expect, it } from 'vitest';

import { parseBoardLink, startTeamThreadPath, teamThreadPath } from './teamBoardLinks';

const team = '11111111-1111-4111-8111-111111111111';
const report = '22222222-2222-4222-8222-222222222222';
const post = '33333333-3333-4333-8333-333333333333';

function parse(path: string) {
  return parseBoardLink(new URL(path, 'https://ase.test').searchParams);
}

describe('team board links', () => {
  it('round-trips a thread and a new report version subject', () => {
    expect(parse(teamThreadPath(team, post))).toEqual({
      teamId: team,
      postId: post,
      subject: null,
    });
    const start = startTeamThreadPath(team, { kind: 'report_version', id: report, version: 3 });
    expect(start.startsWith('/teams?')).toBe(true);
    expect(parse(start)).toEqual({
      teamId: team,
      postId: null,
      subject: { kind: 'report_version', id: report, version: 3 },
    });
    expect(parse(startTeamThreadPath(team, { kind: 'saved_area', id: report }))?.subject).toEqual({
      kind: 'saved_area',
      id: report,
    });
  });

  it('ignores malformed or unrelated links rather than guessing', () => {
    expect(parse('/teams')).toBeNull();
    expect(parse(`/teams?team=${team}`)).toBeNull();
    expect(parse(`/teams?team=not-a-team&board=thread&post=${post}`)).toBeNull();
    expect(parse(`/teams?team=${team}&board=thread&post=<script>`)?.postId).toBeNull();
    const bad = [
      `subject=evidence&subject_id=${report}`,
      `subject=report_version&subject_id=${report}`,
      `subject=report_version&subject_id=${report}&version=0`,
      `subject=report_version&subject_id=${report}&version=1.5`,
      `subject=saved_area&subject_id=${report}&version=2`,
      `subject=saved_area&subject_id=nope`,
    ];
    for (const query of bad) {
      expect(parse(`/teams?team=${team}&board=thread&${query}`)?.subject).toBeNull();
    }
  });
});

import { describe, expect, it } from 'vitest';
import { report as fixture } from '@/test/fixtures';
import { briefingKeyPoints, briefingLead, briefingPassage } from './cyberBriefingModel';

function briefing() {
  const report = structuredClone(fixture);
  report.version.body.assessment = [
    {
      heading: 'Nation-state activity',
      text: 'Reporting names APT29 activity against cloud accounts. Attribution is the source’s.',
      evidence: [],
    },
    { heading: 'GNSS interference and navigation warfare', text: '   ', evidence: [] },
  ];
  report.version.body.reporting = [
    {
      theme: 'Ukraine',
      items: [
        { text: 'CERT-UA described a phishing wave.', evidence: [], grade: 'F6' },
        { text: 'An outage signal was recorded in Kyiv.', evidence: [], grade: 'B2' },
      ],
    },
  ];
  return report;
}

describe('cyber briefing passages', () => {
  it('finds themed analysis or reporting by heading and never invents a passage', () => {
    const report = briefing();
    expect(briefingPassage(report, 'nation_state')?.text).toMatch(/APT29 activity/);
    expect(briefingPassage(report, 'ukraine')?.text).toBe(
      'CERT-UA described a phishing wave. An outage signal was recorded in Kyiv.',
    );
    expect(briefingPassage(report, 'gnss_interference')).toBeNull();
    expect(briefingPassage(report, 'nato_allies')).toBeNull();
  });

  it('bounds long passages on a sentence or word boundary', () => {
    const report = briefing();
    report.version.body.assessment = [
      {
        heading: 'UK critical national infrastructure',
        text: `${'word '.repeat(200)}end.`,
        evidence: [],
      },
    ];
    const passage = briefingPassage(report, 'uk_infrastructure');
    expect(passage?.text.length).toBeLessThanOrEqual(701);
    expect(passage?.text.endsWith('…')).toBe(true);
  });

  it('reads the executive lead and bounded key points from the saved report', () => {
    const report = briefing();
    expect(briefingLead(report)?.text).toBeTruthy();
    expect(briefingKeyPoints(report, 2).length).toBeLessThanOrEqual(2);
  });
});

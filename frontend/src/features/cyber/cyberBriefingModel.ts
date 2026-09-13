/** Reads themed passages out of a saved cyber briefing without generating new claims. */
import { intelligenceSummaryModel } from '@/components/research/intelligenceSummaryModel';
import type { CyberTheme } from '@/lib/api/cyber';
import type { Report } from '@/lib/api/reports';
import { CYBER_THEME_META } from '@/lib/cyberThemes';

export interface ThemePassage {
  heading: string;
  text: string;
  evidence: string[];
}

const MAX_PASSAGE = 700;

function trim(text: string): string {
  const compact = text.trim().replace(/\s+/g, ' ');
  if (compact.length <= MAX_PASSAGE) return compact;
  const cut = compact.slice(0, MAX_PASSAGE);
  return `${cut.slice(0, Math.max(cut.lastIndexOf('. '), cut.lastIndexOf(' ')))}…`;
}

/**
 * The first authored analysis or reporting section whose heading names the lens.
 * Returns null when the briefing carries no such heading; nothing is inferred.
 */
export function briefingPassage(report: Report, theme: CyberTheme): ThemePassage | null {
  const summary = intelligenceSummaryModel(report);
  const fragments = CYBER_THEME_META[theme].briefingHeadings;
  const matches = (heading: string) => {
    const folded = heading.toLocaleLowerCase();
    return fragments.some((fragment) => folded.includes(fragment));
  };
  const analysis = summary.analysis.find((section) => matches(section.heading));
  if (analysis?.text.trim()) {
    return { heading: analysis.heading, text: trim(analysis.text), evidence: analysis.evidence };
  }
  const group = summary.developments.find((row) => matches(row.theme));
  if (group?.items.length) {
    return {
      heading: group.theme,
      text: trim(group.items.map((item) => item.text).join(' ')),
      evidence: [...new Set(group.items.flatMap((item) => item.evidence))],
    };
  }
  return null;
}

export function briefingLead(report: Report): { text: string; evidence: string[] } | null {
  const summary = intelligenceSummaryModel(report);
  return summary.lead ? { text: trim(summary.lead.text), evidence: summary.lead.evidence } : null;
}

export function briefingKeyPoints(
  report: Report,
  limit = 4,
): { text: string; evidence: string[] }[] {
  return intelligenceSummaryModel(report)
    .keyPoints.slice(0, limit)
    .map((point) => ({ text: trim(point.text), evidence: point.evidence }));
}

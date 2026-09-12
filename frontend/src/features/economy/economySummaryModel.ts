import type { Report } from '@/lib/api/reports';

export interface EconomySummaryPoint {
  text: string;
  evidence: string[];
}

const textKey = (text: string) => text.trim().replace(/\s+/g, ' ');

/** A bounded reading preview of authored content, with no generated or inferred claims. */
export function economySummaryModel(report: Report) {
  const { body, evidence } = report.version;
  const judgements = body.key_judgements.slice(0, 8).map((item) => ({
    text: item.statement,
    evidence: [...item.supporting_evidence, ...item.contradicting_evidence],
  }));
  const assessment = body.assessment.slice(0, 12);
  const reporting = body.reporting.slice(0, 8).map((group) => ({
    ...group,
    items: group.items.slice(0, 3),
  }));
  const candidates = [...judgements, ...assessment, ...reporting.flatMap((group) => group.items)];
  const evidenceByText = new Map<string, Set<string>>();
  for (const item of candidates) {
    const key = textKey(item.text);
    const labels = evidenceByText.get(key) ?? new Set<string>();
    item.evidence.forEach((label) => labels.add(label));
    evidenceByText.set(key, labels);
  }
  const shown = new Set<string>();
  const take = (item: EconomySummaryPoint | undefined): EconomySummaryPoint | null => {
    if (!item) return null;
    const key = textKey(item.text);
    if (!key || shown.has(key)) return null;
    shown.add(key);
    return { text: item.text.trim(), evidence: [...(evidenceByText.get(key) ?? [])] };
  };
  const leadCandidate = [...judgements, ...assessment].find((item) => textKey(item.text));
  const lead = take(leadCandidate);
  const keyPoints = judgements.map(take).filter((item) => item !== null);
  const analysis = assessment.flatMap((item) => {
    const point = take(item);
    return point ? [{ ...point, heading: item.heading }] : [];
  });
  const developments = reporting
    .map((group) => ({
      theme: group.theme,
      items: group.items.map(take).filter((item) => item !== null),
    }))
    .filter((group) => group.items.length > 0);
  const visible = [...(lead ? [lead] : []), ...keyPoints, ...analysis];
  const used = new Set([
    ...visible.flatMap((item) => item.evidence),
    ...developments.flatMap((group) => group.items.flatMap((item) => item.evidence)),
  ]);
  const references = evidence.filter((item) => used.has(item.label));
  const knownLabels = new Set(references.map((item) => item.label));
  return {
    lead,
    keyPoints,
    analysis,
    developments,
    references,
    missingReferences: [...used].some((label) => !knownLabels.has(label)),
    watch: [
      ...new Set(
        body.key_judgements
          .slice(0, 8)
          .flatMap((item) => item.indicators)
          .filter(Boolean),
      ),
    ].slice(0, 8),
    gaps: body.gaps.slice(0, 4),
  };
}

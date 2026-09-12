import type { Report } from '@/lib/api/reports';
import type { JudgementAssessment } from '@/lib/api/reportAssessment';

export interface SummaryJudgement {
  id: string;
  probability: string;
  confidence: string;
  rationale: string;
  supportingEvidence: string[];
  contraryEvidence: string[];
  assessment: JudgementAssessment | undefined;
}

interface SummaryPoint {
  text: string;
  evidence: string[];
  judgements?: SummaryJudgement[];
}

const textKey = (text: string) => text.trim().replace(/\s+/g, ' ');

function confidenceRationale(statement: string, assessment: JudgementAssessment | undefined) {
  const marker = 'Model rationale (unverified): ';
  // The saved engine decision is displayed separately; preserve all other authored text.
  if (
    assessment &&
    statement.startsWith('Engine confidence ceiling: ') &&
    statement.includes(marker)
  )
    return statement.slice(statement.indexOf(marker) + marker.length);
  return statement;
}

/** A bounded reading preview of authored content, with no generated or inferred claims. */
export function intelligenceSummaryModel(report: Report) {
  const { body, evidence } = report.version;
  const judgements = body.key_judgements.slice(0, 8).map((item) => {
    const assessment = report.version.assessment?.judgements.find(
      (recorded) => recorded.judgement_id === item.id,
    );
    return {
      text: item.statement,
      evidence: [...item.supporting_evidence, ...item.contradicting_evidence],
      judgements: [
        {
          id: item.id,
          probability: item.probability,
          confidence: item.confidence,
          rationale: confidenceRationale(item.confidence_statement, assessment),
          supportingEvidence: item.supporting_evidence,
          contraryEvidence: item.contradicting_evidence,
          assessment,
        },
      ],
    };
  });
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
  const take = (item: SummaryPoint | undefined): SummaryPoint | null => {
    if (!item) return null;
    const key = textKey(item.text);
    if (!key || shown.has(key)) return null;
    shown.add(key);
    return {
      text: item.text.trim(),
      evidence: [...(evidenceByText.get(key) ?? [])],
      judgements: judgements
        .filter((judgement) => textKey(judgement.text) === key)
        .flatMap((judgement) => judgement.judgements),
    };
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

const reliabilityLabels = [
  'completely reliable',
  'usually reliable',
  'fairly reliable',
  'not usually reliable',
  'unreliable',
  'reliability cannot be judged',
];
const credibilityLabels = [
  'confirmed',
  'probably true',
  'possibly true',
  'doubtful',
  'improbable',
  'cannot be judged',
];

/** Explain a recorded A-F / 1-6 grade without assigning or changing either dimension. */
export function sourceGradeDescription(grade: string): string {
  const normalised = grade.trim();
  if (!/^[A-F][1-6]$/.test(normalised))
    return 'The recorded grade has no recognised scale description.';
  const reliabilityCode = normalised.charAt(0);
  const credibilityCode = normalised.charAt(1);
  return `Grade key: ${reliabilityCode} = source ${reliabilityLabels['ABCDEF'.indexOf(reliabilityCode)]}; ${credibilityCode} = information ${credibilityLabels[Number(credibilityCode) - 1]}.`;
}

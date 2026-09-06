import type { ReportAssessment } from '@/lib/api/reportAssessment';
import type { ReportMethodology } from '@/lib/api/reportMethodology';

export const reportAssessment: ReportAssessment = {
  method_version: 'ase-evidence-test',
  evidence: [
    {
      label: 'E1',
      event_id: 'e1',
      source_id: 'bbc_world',
      reliability: 'B',
      credibility: 2,
      contribution: 'strong',
      organisation: 'org-one',
      flags: [],
      reasons: ['B2 permits a strong contribution.'],
    },
    {
      label: 'E2',
      event_id: 'e2',
      source_id: 'tass_en',
      reliability: 'C',
      credibility: 3,
      contribution: 'limited',
      organisation: null,
      flags: ['state_controlled'],
      reasons: ['Credibility is limited.'],
    },
  ],
  judgements: [
    {
      judgement_id: 'KJ1',
      supporting_labels: ['E1'],
      contradicting_labels: ['E2'],
      invalid_labels: ['E9'],
      support_groups: [
        {
          id: 'declared-one',
          labels: ['E1'],
          known_organisation: true,
          contribution: 'strong',
          confirmed_strong: false,
          corroborating_contribution: 'strong',
          possible_copy: false,
        },
      ],
      opposition_groups: [
        {
          id: 'unknown-two',
          labels: ['E2'],
          known_organisation: false,
          contribution: 'limited',
          confirmed_strong: false,
          corroborating_contribution: 'unassessed',
          possible_copy: false,
        },
      ],
      support_tier: 'strong',
      opposition_tier: 'limited',
      balance: 'support_stronger',
      status: 'contested',
      confidence_ceiling: 'moderate',
      final_confidence: 'low',
      explanation: ['A strong supporting group outweighs limited opposing evidence.'],
      limitations: ['The opposing source has unknown provenance.'],
      improvements: ['Seek separately sourced reporting that addresses the opposition.'],
    },
  ],
  tallies: {
    evidence_items: 2,
    declared_groups: 1,
    unknown_provenance_items: 1,
    possible_copy_groups: 0,
    judgements: 1,
    strong: 1,
    moderate: 0,
    limited: 1,
    unassessed: 0,
    supported_judgements: 0,
    limited_judgements: 0,
    contested_judgements: 1,
    unsupported_judgements: 0,
  },
  validation_errors: 0,
  validation_warnings: 1,
  limitations: [
    'This application policy is not an official NATO scoring algorithm or a truth probability.',
  ],
};

// Deliberately synthetic policy cells verify that the view displays the API response.
export const reportMethodology: ReportMethodology = {
  method_version: 'ase-evidence-test-current',
  title: 'Automated evidence contribution and confidence limits',
  contribution_matrix: ['A', 'B', 'C', 'D', 'E', 'F'].flatMap((reliability) =>
    Array.from({ length: 6 }, (_, index) => ({
      reliability,
      credibility: index + 1,
      contribution: reliability === 'F' ? ('unassessed' as const) : ('limited' as const),
    })),
  ),
  reliability_scale: [
    'Completely reliable',
    'Usually reliable',
    'Fairly reliable',
    'Not usually reliable',
    'Unreliable',
    'Reliability cannot be judged',
  ].map((label, index) => ({ grade: 'ABCDEF'[index]!, label })),
  credibility_scale: [
    'Confirmed',
    'Probably true',
    'Possibly true',
    'Doubtful',
    'Improbable',
    'Cannot be judged',
  ].map((label, index) => ({ grade: index + 1, label })),
  assessment_dimensions: [
    {
      name: 'Information base',
      engine_assessed: true,
      description: 'The available evidence and its limitations.',
    },
    {
      name: 'Analytical rigour',
      engine_assessed: false,
      description: 'Not independently measured by this engine.',
    },
  ],
  confidence_rules: ['A confidence limit cannot raise the model confidence.'],
  limitations: ['Supporting and opposing relationships remain model-assigned.'],
  doctrine_references: [{ title: 'Doctrinal reference', url: 'https://example.org/doctrine' }],
  probability_yardstick: [
    {
      probability: 'highly_likely',
      term: 'Highly likely',
      low_percent: 80,
      high_percent: 90,
      range_description: 'About 80% to about 90%',
    },
  ],
};

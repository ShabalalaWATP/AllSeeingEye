/**
 * The Ask, Collect and Assess chapters. Every capability here exists in the current
 * backend (application/research, application/reports and domain/grading); the
 * question and report text are illustrative and are never generated live.
 */

export const EXAMPLE_QUESTION =
  'What is driving the recent fall in commercial shipping through the Bab el-Mandeb strait?';

export interface ScopeChip {
  label: string;
  value: string;
  /** Carried over from the area selected on the map in the Observe chapter. */
  fromMap?: boolean;
}

export const SCOPE_CHIPS: readonly ScopeChip[] = [
  { label: 'Area', value: 'Drawn on the map', fromMap: true },
  { label: 'Region', value: 'Red Sea and Gulf of Aden' },
  { label: 'Countries', value: 'Yemen · Djibouti · Eritrea' },
  { label: 'Window', value: 'Last 14 days' },
  { label: 'Languages', value: 'English · Arabic' },
  { label: 'Template', value: 'Maritime activity report' },
];

export const DEPTHS: readonly { name: string; words: string; evidence: number }[] = [
  { name: 'Basic', words: '750 to 1,350 words', evidence: 24 },
  { name: 'Deep', words: '1,800 to 3,000 words', evidence: 48 },
  { name: 'Advanced', words: '3,750 to 6,000 words', evidence: 80 },
];

export const ASK_FEATURES: readonly string[] = [
  'Ten report templates, from intelligence summaries to disaster SITREPs',
  'Twenty research presets and saved Research Briefs',
  'Area research from a polygon drawn on the map',
  'Company, domain, document and media focus',
  'Query translation and transliteration across languages',
  'Photo geolocation with a sun and shadow check',
  'Private documents and media as inputs, analysed by your configured AI provider',
];

export interface EvidenceCard {
  id: string;
  family: string;
  title: string;
  grade: string;
  collected: string;
  /** Illustrative collection receipt reference; real receipts record each source task. */
  receipt: string;
  gap?: boolean;
}

export const EVIDENCE: readonly EvidenceCard[] = [
  {
    id: 'e1',
    family: 'Maritime',
    title: 'Navigation warning, southern Red Sea',
    grade: 'B2',
    collected: '06:40 UTC',
    receipt: '7f3a·91c2',
  },
  {
    id: 'e2',
    family: 'Economic',
    title: 'Port call statistics, weekly series',
    grade: 'A2',
    collected: '07:05 UTC',
    receipt: '0b6e·d417',
  },
  {
    id: 'e3',
    family: 'News',
    title: 'Regional broadcaster, Arabic language',
    grade: 'C3',
    collected: '07:12 UTC',
    receipt: 'c52d·08fa',
  },
  {
    id: 'e4',
    family: 'Political',
    title: 'Government statement on transit security',
    grade: 'B3',
    collected: '07:30 UTC',
    receipt: '9a14·6e3b',
  },
  {
    id: 'e5',
    family: 'Social',
    title: 'Unverified video of a vessel incident',
    grade: 'F6',
    collected: '07:41 UTC',
    receipt: 'e7c0·2d95',
  },
  {
    id: 'gap',
    family: 'Gap',
    title: 'No independent satellite confirmation found',
    grade: 'Gap',
    collected: 'Open',
    receipt: '41f8·b0c6',
    gap: true,
  },
];

export const SHARED_ORIGIN =
  'Similar reports may share one original source, so copies are grouped rather than counted as extra confirmation.';

export const GRADING = {
  reliability: 'Source reliability A to F',
  credibility: 'Information credibility 1 to 6',
  note: 'F and 6 mean the source or claim cannot yet be judged. New research material without an assessed source basis stays unassessed.',
};

export interface Judgement {
  id: string;
  text: string;
  likelihood: string;
  /** Set per judgement: the engine never gives a whole report one confidence level. */
  confidence: 'High' | 'Moderate' | 'Low';
  cites: readonly string[];
  challenged?: boolean;
}

export const JUDGEMENTS: readonly Judgement[] = [
  {
    id: 'j1',
    text: 'Transit volumes have fallen because insurers and operators are rerouting around the strait.',
    likelihood: 'Highly likely',
    confidence: 'Moderate',
    cites: ['e1', 'e2'],
  },
  {
    id: 'j2',
    text: 'Recent incidents reported in the area are the main driver of the rerouting decisions.',
    likelihood: 'Likely',
    confidence: 'Moderate',
    cites: ['e3', 'e4'],
    challenged: true,
  },
  {
    id: 'j3',
    text: 'The reported vessel attack shown in circulating video took place this week.',
    likelihood: 'Realistic possibility',
    confidence: 'Low',
    cites: ['e5'],
  },
];

/** Report header. The model line names no model: none is bundled, each installation chooses. */
export const REPORT_HEADER = {
  title: 'Shipping through the Bab el-Mandeb strait',
  summary: 'Maritime activity report · Confidence stated per judgement',
  model: 'Deep research · Model: your configured provider · AI-assisted assessment',
};

/** The closing beat: a saved report keeps living through versions and follow-ups. */
export const REPORT_NEXT: readonly string[] = [
  'Saved as version 1',
  'Follow-up question in the same scope',
  'Regenerate as version 2 and compare',
];

export const ALTERNATIVE =
  'Alternative explanation: seasonal demand and longer-running freight rate changes account for part of the fall.';

export const ASSESS_CHECKS: readonly string[] = [
  'Probability language checked against the PHIA yardstick',
  'High, moderate or low confidence, capped by the evidence',
  'Citation, entailment and contradiction checks',
  'Challenge pass and devil’s advocacy on the top judgement',
  'Alternative hypotheses, assumptions and information gaps',
  'Claims ledger with identities and relationships to review',
  'Exact calculations with formula receipts',
];

export const PHIA_BANDS: readonly string[] = [
  'Remote chance',
  'Highly unlikely',
  'Unlikely',
  'Realistic possibility',
  'Likely',
  'Highly likely',
  'Almost certain',
];

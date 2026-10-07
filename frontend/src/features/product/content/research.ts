/**
 * The Ask, Collect and Assess chapters. Every capability here exists in the current
 * backend (application/research, application/reports and domain/grading); the
 * question and report text are illustrative and are never generated live.
 */

export const EXAMPLE_QUESTION =
  'What is driving the recent fall in commercial shipping through the Bab el-Mandeb strait?';

export const SCOPE_CHIPS: readonly { label: string; value: string }[] = [
  { label: 'Region', value: 'Red Sea and Gulf of Aden' },
  { label: 'Countries', value: 'Yemen · Djibouti · Eritrea' },
  { label: 'Window', value: 'Last 30 days' },
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
];

export interface EvidenceCard {
  id: string;
  family: string;
  title: string;
  grade: string;
  collected: string;
  gap?: boolean;
}

export const EVIDENCE: readonly EvidenceCard[] = [
  {
    id: 'e1',
    family: 'Maritime',
    title: 'Navigation warning, southern Red Sea',
    grade: 'B2',
    collected: '06:40 UTC',
  },
  {
    id: 'e2',
    family: 'Economic',
    title: 'Port call statistics, weekly series',
    grade: 'A2',
    collected: '07:05 UTC',
  },
  {
    id: 'e3',
    family: 'News',
    title: 'Regional broadcaster, Arabic language',
    grade: 'C3',
    collected: '07:12 UTC',
  },
  {
    id: 'e4',
    family: 'Political',
    title: 'Government statement on transit security',
    grade: 'B3',
    collected: '07:30 UTC',
  },
  {
    id: 'e5',
    family: 'Social',
    title: 'Unverified video of a vessel incident',
    grade: 'F6',
    collected: '07:41 UTC',
  },
  {
    id: 'gap',
    family: 'Gap',
    title: 'No independent satellite confirmation found',
    grade: 'Gap',
    collected: 'Open',
    gap: true,
  },
];

export const GRADING = {
  reliability: 'Source reliability A to F',
  credibility: 'Information credibility 1 to 6',
  note: 'F and 6 mean the source or claim cannot yet be judged. On-demand results start unassessed until reviewed.',
};

export interface Judgement {
  id: string;
  text: string;
  likelihood: string;
  cites: readonly string[];
  challenged?: boolean;
}

export const JUDGEMENTS: readonly Judgement[] = [
  {
    id: 'j1',
    text: 'Transit volumes have fallen because insurers and operators are rerouting around the strait.',
    likelihood: 'Highly likely',
    cites: ['e1', 'e2'],
  },
  {
    id: 'j2',
    text: 'Recent incidents reported in the area are the main driver of the rerouting decisions.',
    likelihood: 'Likely',
    cites: ['e3', 'e4'],
    challenged: true,
  },
  {
    id: 'j3',
    text: 'The reported vessel attack shown in circulating video took place this week.',
    likelihood: 'Realistic possibility',
    cites: ['e5'],
  },
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

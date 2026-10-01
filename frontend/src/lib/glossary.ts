/**
 * Plain-language explanations for research terms, rendered as React text only. The evidence
 * grade wording repeats the evidence annex, and likelihood bands come from the server's
 * configured yardstick (see useYardstick), never from this file.
 */
export interface GlossaryEntry {
  id: string;
  term: string;
  text: string;
}

export const REQUIREMENT_CODES = {
  PIR: 'priority intelligence requirement',
  SIR: 'specific intelligence requirement',
  EEI: 'essential element of information',
} as const;
export type RequirementCode = keyof typeof REQUIREMENT_CODES;

export const GLOSSARY_PATH = '/help#glossary';
export const glossaryPath = (id: string) => `/help#glossary-${id}`;

export const GLOSSARY: readonly GlossaryEntry[] = [
  {
    id: 'pir',
    term: 'PIR (priority intelligence requirement)',
    text: 'The main question a plan or report serves. Plans and reports number them PIR-1, PIR-2 and so on.',
  },
  {
    id: 'sir',
    term: 'SIR (specific intelligence requirement)',
    text: "A narrower question that helps answer a PIR. A plan's SIRs carry the keywords and categories matched against connected feeds.",
  },
  {
    id: 'eei',
    term: 'EEI (essential element of information)',
    text: 'A specific fact needed to answer a requirement, such as a place, actor or date. A gap may name the EEI it leaves unanswered.',
  },
  {
    id: 'likelihood',
    term: 'Likelihood',
    text: 'How probable a judgement is, in the words of the UK Probability Yardstick. Each word stands for an approximate band, not a measured probability. A term without a configured band is shown as such rather than given a guessed range.',
  },
  {
    id: 'confidence',
    term: 'Confidence',
    text: 'How strong and stable the basis for a judgement is: high, moderate or low. It is separate from likelihood: a likely judgement can rest on a weak basis.',
  },
  {
    id: 'source-grades',
    term: 'Source reliability and information credibility',
    text: "Each saved grade separates source reliability (A to F), the source's record and ability to report reliably, from information credibility (1 to 6), how far other reporting supports this item. F6 means there was not enough basis to judge, not that the report was false. A grade describes the source and the information; it is not proof that a claim is true.",
  },
  {
    id: 'alert-rule',
    term: 'Alert rule',
    text: 'A standing check on connected feeds that raises an alert when enough matching items arrive within its time window. Alert rules match keywords literally; they do not interpret meaning. The API and saved data call an alert rule an indicator.',
  },
  {
    id: 'indicators-and-warning',
    term: 'Indicators and warning',
    text: "The part of a report that says what to watch for and the current watch condition. A report's indicators are analytical wording, which an alert rule can only approximate with keywords.",
  },
];

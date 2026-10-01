import type {
  QualityJobGroup,
  QualityVersionGroup,
  ResearchQuality,
} from '@/lib/api/researchQuality';

const COUNT = new Intl.NumberFormat('en-GB');

export const formatCount = (value: number): string => COUNT.format(value);

export const plural = (count: number, one: string, many = `${one}s`): string =>
  `${formatCount(count)} ${count === 1 ? one : many}`;

export type QualityDimension = 'template' | 'depth' | 'connection';

export const DIMENSIONS: { id: QualityDimension; label: string }[] = [
  { id: 'template', label: 'Template' },
  { id: 'depth', label: 'Depth' },
  { id: 'connection', label: 'Model connection' },
];

export function versionGroups(
  data: ResearchQuality,
  dimension: QualityDimension,
): QualityVersionGroup[] {
  const { versions } = data;
  if (dimension === 'template') return versions.by_template;
  if (dimension === 'depth') return versions.by_depth;
  return versions.by_connection;
}

/** Jobs record the model name rather than the connection, so that split is by model. */
export function jobGroups(data: ResearchQuality, dimension: QualityDimension): QualityJobGroup[] {
  const { jobs } = data;
  if (dimension === 'template') return jobs.by_template;
  if (dimension === 'depth') return jobs.by_depth;
  return jobs.by_model;
}

export function versionCaption(dimension: QualityDimension): string {
  return `Saved version outcomes by ${dimension === 'connection' ? 'model connection' : dimension}`;
}

export function jobCaption(dimension: QualityDimension): string {
  return `Report job outcomes by ${dimension === 'connection' ? 'model' : dimension}`;
}

interface Population {
  bound: number;
  in_window: number;
  counted: number;
  bound_reached: boolean;
}

export function populationText(noun: string, value: Population, windowDays: number): string {
  const counted = `${formatCount(value.counted)} of ${plural(value.in_window, noun)} from the last ${windowDays} days`;
  return value.bound_reached
    ? `${counted}. Only the newest ${formatCount(value.bound)} of ${plural(value.in_window, noun)} are counted.`
    : `${counted}.`;
}

export function findingText(versions: number, occurrences: number, denominator: number): string {
  return `${formatCount(versions)} of ${plural(denominator, 'version')}, ${plural(occurrences, 'occurrence')}`;
}

export function receiptText(group: QualityVersionGroup): string {
  const { receipts } = group;
  if (receipts.versions_with_receipts === 0) return 'No research receipts';
  return `${formatCount(receipts.versions_with_empty_or_unavailable)} of ${plural(receipts.versions_with_receipts, 'version')} with receipts`;
}

export function usageText(group: QualityVersionGroup): string {
  const { usage } = group;
  if (usage.prompt_tokens_per_version === null || usage.completion_tokens_per_version === null)
    return `No token counts recorded for ${plural(group.versions, 'version')}`;
  return `${formatCount(usage.prompt_tokens_per_version)} prompt and ${formatCount(usage.completion_tokens_per_version)} completion tokens per version, from ${formatCount(usage.versions_with_usage)} of ${plural(group.versions, 'version')}`;
}

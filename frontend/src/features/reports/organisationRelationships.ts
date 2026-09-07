import { z } from 'zod';
import type { EvidenceItem } from '@/lib/api/reports';

const kinds = {
  'research-gleif-direct-parent': 'IS_DIRECTLY_CONSOLIDATED_BY',
  'research-gleif-ultimate-parent': 'IS_ULTIMATELY_CONSOLIDATED_BY',
} as const;
const periodSchema = z
  .array(
    z
      .object({
        type: z.string().max(50),
        startDate: z.string().max(50),
        endDate: z.string().max(50),
      })
      .strict(),
  )
  .max(20);

export interface ReportedRelationship {
  evidence: EvidenceItem;
  child: string;
  parent: string;
  kind: 'direct' | 'ultimate';
  attributes: ReadonlyMap<string, string | number | boolean | null>;
  periods: z.infer<typeof periodSchema> | null;
}

/** Display only explicit retained source assertions; never infer or merge an edge. */
export function organisationRelationships(evidence: readonly EvidenceItem[]) {
  const rows: ReportedRelationship[] = [];
  const unusable: string[] = [];
  for (const item of evidence) {
    if (!Object.hasOwn(kinds, item.source_id)) continue;
    const source = item.source_id as keyof typeof kinds;
    const attributes = new Map((item.attributes ?? []).map(({ key, value }) => [key, value]));
    const child = attributes.get('child_lei');
    const parent = attributes.get('parent_lei');
    if (
      attributes.size !== item.attributes?.length ||
      attributes.get('record_kind') !== 'reported_accounting_consolidation' ||
      attributes.get('reported_relationship_type') !== kinds[source] ||
      typeof child !== 'string' ||
      !/^[A-Z0-9]{18}[0-9]{2}$/.test(child) ||
      typeof parent !== 'string' ||
      !/^[A-Z0-9]{18}[0-9]{2}$/.test(parent)
    ) {
      unusable.push(item.label);
      continue;
    }
    let periods: ReportedRelationship['periods'] = null;
    const raw = attributes.get('reported_periods');
    if (typeof raw === 'string' && raw.length <= 500) {
      try {
        const parsed = periodSchema.safeParse(JSON.parse(raw));
        if (parsed.success) periods = parsed.data;
      } catch {
        /* The original value remains in the evidence annex. */
      }
    }
    rows.push({
      evidence: item,
      child,
      parent,
      kind: source === 'research-gleif-direct-parent' ? 'direct' : 'ultimate',
      attributes,
      periods,
    });
  }
  return { rows, unusable };
}

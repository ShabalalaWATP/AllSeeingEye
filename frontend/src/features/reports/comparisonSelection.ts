import { fetchClaim, listClaims } from '@/lib/api/claims';
import type { ClaimRevision } from '@/lib/api/claims';
import { fetchIdentity, listIdentities } from '@/lib/api/identities';
import type { IdentityRevision } from '@/lib/api/identities';
import { fetchRelationship, listRelationships } from '@/lib/api/relationships';
import type { RelationshipRevision } from '@/lib/api/relationships';
export type ComparisonAnnotation = ClaimRevision | IdentityRevision | RelationshipRevision;
export type AnnotationKind = 'claim' | 'identity' | 'relationship';
export function annotationKind(value: ComparisonAnnotation): AnnotationKind {
  return 'claim_id' in value ? 'claim' : 'decision_id' in value ? 'identity' : 'relationship';
}
export function annotationRoot(value: ComparisonAnnotation): string {
  return 'claim_id' in value
    ? value.claim_id
    : 'decision_id' in value
      ? value.decision_id
      : value.relationship_id;
}
export const annotationKey = (value: ComparisonAnnotation) =>
  `${annotationKind(value)}:${value.id}`;
export function annotationTitle(value: ComparisonAnnotation): string {
  return 'statement' in value
    ? value.statement
    : 'subject' in value
      ? `${value.subject}: ${value.candidate.candidate.evidence_label}`
      : `${value.assertion.kind} parent ${value.assertion.child_lei} to ${value.assertion.parent_lei}`;
}
export function listAnnotations(
  kind: AnnotationKind,
  reportId: string,
  version: number,
  offset: number,
  signal: AbortSignal,
): Promise<
  Omit<Awaited<ReturnType<typeof listClaims>>, 'items'> & { items: ComparisonAnnotation[] }
> {
  const fetcher =
    kind === 'claim' ? listClaims : kind === 'identity' ? listIdentities : listRelationships;
  return fetcher(reportId, version, offset, signal);
}
export async function fetchAnnotation(
  value: ComparisonAnnotation,
  revisionId: string,
  signal: AbortSignal,
): Promise<ComparisonAnnotation> {
  const fetcher =
    'claim_id' in value ? fetchClaim : 'decision_id' in value ? fetchIdentity : fetchRelationship;
  return (await fetcher(annotationRoot(value), revisionId, signal)).revision;
}

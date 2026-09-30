import { expect, it, vi } from 'vitest';
import { comparisonClaim } from '@/test/fixtures.comparisons';
import { identityRevision, identityRoot } from '@/test/fixtures.identities';
import { relationshipRevision, relationshipRoot } from '@/test/fixtures.relationships';
import { claimRevisionSchema, fetchClaim, listClaims } from '@/lib/api/claims';
import { fetchIdentity, listIdentities } from '@/lib/api/identities';
import { fetchRelationship, listRelationships } from '@/lib/api/relationships';
import {
  annotationKey,
  annotationRoot,
  annotationTitle,
  fetchAnnotation,
  listAnnotations,
  toComparisonSelection,
} from './comparisonSelection';

vi.mock('@/lib/api/claims', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/lib/api/claims')>()),
  fetchClaim: vi.fn(),
  listClaims: vi.fn(),
}));
vi.mock('@/lib/api/identities', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/lib/api/identities')>()),
  fetchIdentity: vi.fn(),
  listIdentities: vi.fn(),
}));
vi.mock('@/lib/api/relationships', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/lib/api/relationships')>()),
  fetchRelationship: vi.fn(),
  listRelationships: vi.fn(),
}));

it('keeps mixed annotation roots and exact selected revisions in separate request fields', () => {
  const selection = toComparisonSelection({
    reportId: 'selected-report',
    version: 3,
    annotations: [relationshipRevision, comparisonClaim, identityRevision],
  });
  expect(selection).toEqual({
    report_id: 'selected-report',
    version_number: 3,
    revisions: [{ claim_id: comparisonClaim.claim_id, revision_id: comparisonClaim.id }],
    identity_revisions: [
      { decision_id: identityRevision.decision_id, revision_id: identityRevision.id },
    ],
    relationship_revisions: [
      {
        relationship_id: relationshipRevision.relationship_id,
        revision_id: relationshipRevision.id,
      },
    ],
  });
  expect(toComparisonSelection({ reportId: 'empty', version: 1, annotations: [] })).toEqual({
    report_id: 'empty',
    version_number: 1,
    revisions: [],
    identity_revisions: [],
    relationship_revisions: [],
  });
});

it('namespaces revision keys even when different annotation kinds share the same identifier', () => {
  const values = [comparisonClaim, identityRevision, relationshipRevision].map((item) => ({
    ...item,
    id: 'same-revision',
  }));
  expect(values.map(annotationKey)).toEqual([
    'claim:same-revision',
    'identity:same-revision',
    'relationship:same-revision',
  ]);
  expect(values.map(annotationRoot)).toEqual(['claim-1', 'identity-1', 'relationship-1']);
  expect(values.map(annotationTitle)).toEqual([
    comparisonClaim.statement,
    `${identityRevision.subject}: E1`,
    'direct parent 00123456789012345678 to 99123456789012345678',
  ]);
});

it.each([
  ['claim', comparisonClaim, listClaims],
  ['identity', identityRevision, listIdentities],
  ['relationship', relationshipRevision, listRelationships],
] as const)(
  'passes the report version, page and cancellation signal to %s inventory',
  async (kind, item, fetcher) => {
    const page = { items: [item], offset: 20, limit: 20, total: 21 };
    vi.mocked(listClaims).mockResolvedValue({
      ...page,
      items: [claimRevisionSchema.parse(comparisonClaim)],
    });
    vi.mocked(listIdentities).mockResolvedValue({ ...page, items: [identityRevision] });
    vi.mocked(listRelationships).mockResolvedValue({ ...page, items: [relationshipRevision] });
    const signal = new AbortController().signal;
    expect(await listAnnotations(kind, 'report-selected', 4, 20, signal)).toEqual(page);
    expect(fetcher).toHaveBeenCalledWith('report-selected', 4, 20, signal);
  },
);

it('fetches the requested historical identity and relationship revisions without using latest IDs', async () => {
  const identity = { ...identityRevision, id: 'identity-old' };
  const relationship = { ...relationshipRevision, id: 'relationship-old' };
  vi.mocked(fetchIdentity).mockResolvedValue({ root: identityRoot, revision: identity });
  vi.mocked(fetchRelationship).mockResolvedValue({
    root: relationshipRoot,
    revision: relationship,
  });
  const signal = new AbortController().signal;
  expect(await fetchAnnotation(identityRevision, identity.id, signal)).toEqual(identity);
  expect(await fetchAnnotation(relationshipRevision, relationship.id, signal)).toEqual(
    relationship,
  );
  expect(fetchIdentity).toHaveBeenCalledWith('identity-1', 'identity-old', signal);
  expect(fetchRelationship).toHaveBeenCalledWith('relationship-1', 'relationship-old', signal);
});

it('propagates a revoked exact-revision read instead of substituting another annotation', async () => {
  const denied = new Error('Access revoked');
  vi.mocked(fetchClaim).mockRejectedValue(denied);
  const signal = new AbortController().signal;
  await expect(fetchAnnotation(comparisonClaim, 'old-claim', signal)).rejects.toBe(denied);
  expect(fetchClaim).toHaveBeenCalledWith('claim-1', 'old-claim', signal);
  expect(fetchIdentity).not.toHaveBeenCalled();
  expect(fetchRelationship).not.toHaveBeenCalled();
});

import { apiBlob } from './client';
import type { components } from './types.gen';

export type ClaimPackageSelection = components['schemas']['ClaimPackageIn'];

export function fetchClaimPackage(
  reportId: string,
  body: ClaimPackageSelection,
  signal: AbortSignal,
) {
  const route = body.identity_revisions?.length
    ? 'selected-evidence-package'
    : 'claim-evidence-package';
  return apiBlob(`/api/reports/${encodeURIComponent(reportId)}/${route}`, {
    method: 'POST',
    body,
    signal,
    headers: { Accept: 'application/zip' },
  });
}

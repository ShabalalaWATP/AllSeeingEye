/** Only expiring receipt references survive photo-page navigation, never image or source text. */
import { ApiError } from '@/lib/api/errors';
import type { ResearchInputReceipt } from '@/lib/api/researchInputs';
import { subscribeWorkspaceAccess, workspaceRevision } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';

interface ReceiptReference {
  id: string;
  expiresAt: number;
  pendingReports: number;
}
let ownerKey = '';
const references = new Map<string, ReceiptReference>();
const MAX_REFERENCES = 8;

function currentKey() {
  const user = useAuthStore.getState().user;
  return `${user?.id ?? ''}:${user?.role ?? ''}:${user?.is_active ?? false}:${workspaceRevision()}`;
}
function reset() {
  ownerKey = '';
  references.clear();
}
function owned(key: string) {
  if (key !== currentKey()) return false;
  if (ownerKey !== key) {
    reset();
    ownerKey = key;
  }
  for (const [id, reference] of references) {
    if (reference.expiresAt <= Date.now() && reference.pendingReports === 0) references.delete(id);
  }
  return useAuthStore.getState().user?.is_active === true;
}

export function rememberPhotoReceipt(key: string, receipt: ResearchInputReceipt) {
  if (!owned(key) || references.has(receipt.id) || Date.parse(receipt.expires_at) <= Date.now())
    return;
  // The server permits two receipts per account; this defensive bound also covers short overlaps.
  if (references.size >= MAX_REFERENCES) return;
  references.set(receipt.id, {
    id: receipt.id,
    expiresAt: Date.parse(receipt.expires_at),
    pendingReports: 0,
  });
}

export function outstandingPhotoReceipts(key: string): readonly string[] {
  if (!owned(key))
    throw new ApiError(409, 'access_changed', 'Account access changed. Upload the photo again.');
  if ([...references.values()].some((entry) => entry.pendingReports > 0)) {
    throw new ApiError(
      409,
      'photo_in_use',
      'A photo report is still finishing. Try the upload again when it has completed or cancelled.',
    );
  }
  return [...references.keys()];
}

export function forgetPhotoReceipt(key: string, id: string) {
  if (owned(key)) references.delete(id);
}

export function holdPhotoReceipt(key: string, receipt: ResearchInputReceipt): () => void {
  rememberPhotoReceipt(key, receipt);
  const reference = owned(key) ? references.get(receipt.id) : undefined;
  if (!reference) return () => undefined;
  reference.pendingReports += 1;
  let released = false;
  return () => {
    if (!released) reference.pendingReports = Math.max(0, reference.pendingReports - 1);
    released = true;
  };
}

// Logout must clear references even if the photo page is no longer mounted.
const unsubscribeAccount = useAuthStore.subscribe((state, previous) => {
  if (
    state.user?.id !== previous.user?.id ||
    state.user?.role !== previous.user?.role ||
    state.user?.is_active !== previous.user?.is_active ||
    state.status !== previous.status
  )
    reset();
});
const unsubscribeAccess = subscribeWorkspaceAccess(reset);
import.meta.hot?.dispose(() => {
  unsubscribeAccount();
  unsubscribeAccess();
  reset();
});

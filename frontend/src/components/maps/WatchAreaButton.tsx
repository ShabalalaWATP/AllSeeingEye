import { useState } from 'react';
import { useNavigate } from 'react-router';
import { prepareAreaWatch } from '@/lib/areaWatchDraft';
import type { WatchAreaInput } from '@/lib/map/areaWatchGeometry';
import { useAuthStore } from '@/stores/auth';

/** Explicit handoff only. This creates no indicator, network request or model job. */
export function WatchAreaButton({
  area,
  disabled = false,
  hint,
}: {
  area: WatchAreaInput | null;
  disabled?: boolean;
  hint?: string;
}) {
  const navigate = useNavigate();
  const authenticated = useAuthStore(
    (state) => state.status === 'authenticated' && state.user?.is_active === true,
  );
  const [error, setError] = useState<string | null>(null);
  return (
    <div className="space-y-2 rounded border border-cyan/25 bg-cyan/5 p-3">
      <button
        type="button"
        disabled={disabled || area === null || !authenticated}
        className="min-h-10 w-full rounded border border-cyan/40 px-3 text-cyan hover:bg-cyan/10 disabled:opacity-50"
        onClick={() => {
          if (!area) return;
          try {
            prepareAreaWatch(area);
            void navigate('/warning');
          } catch (failure) {
            setError(failure instanceof Error ? failure.message : 'Unable to prepare this area.');
          }
        }}
      >
        Watch this area
      </button>
      <p className="text-xs leading-relaxed text-muted">
        {hint ??
          'Review an editable area indicator in Warning. Nothing is created until you choose Add indicator.'}
      </p>
      {error && (
        <p role="alert" className="text-xs text-critical">
          {error}
        </p>
      )}
    </div>
  );
}

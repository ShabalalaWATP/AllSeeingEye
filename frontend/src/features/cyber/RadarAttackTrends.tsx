import { RadarAttackResults } from '@/components/cyber/RadarAttackResults';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { fetchRadarAttackTrends } from '@/lib/api/cyber';
import { describeError } from '@/lib/api/errors';
import { useScopedResource } from '@/lib/hooks/useScopedResource';

export function RadarAttackTrends({ compact = false }: { compact?: boolean }) {
  const resource = useScopedResource(fetchRadarAttackTrends);
  const data = resource.data;
  return (
    <div aria-label="Cloudflare Radar attack distributions" className="space-y-3">
      {resource.loading && !data && <LoadingNote label="Loading Cloudflare attack trends" />}
      {resource.error && (
        <Alert tone="error">
          {describeError(resource.error)}{' '}
          <button type="button" className="underline" onClick={() => void resource.reload()}>
            Retry
          </button>
        </Alert>
      )}
      {data && <RadarAttackResults data={data} compact={compact} />}
    </div>
  );
}

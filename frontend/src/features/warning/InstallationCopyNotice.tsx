import { Alert, LoadingNote } from '@/components/ui/Alert';
import { getRoutingCapabilities } from '@/lib/api/alertRouting';
import { useResource } from '@/lib/hooks/useResource';

export function InstallationCopyNotice() {
  const result = useResource(getRoutingCapabilities);
  if (result.loading) return <LoadingNote label="Checking installation notification copies" />;
  if (!result.data)
    return (
      <Alert tone="warning">
        Installation copy settings could not be checked. Do not assume alerts stay in the
        application.
      </Alert>
    );
  return result.data.installation_copy_enabled ? (
    <Alert tone="warning" title="Installation-wide copy enabled">
      {result.data.installation_copy_notice}
    </Alert>
  ) : (
    <p className="text-xs text-muted">
      No installation-wide webhook copy is configured. Alerts are always stored in the application.
    </p>
  );
}

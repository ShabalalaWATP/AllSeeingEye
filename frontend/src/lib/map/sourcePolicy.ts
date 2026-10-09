/** Browser requests use the server's installation policy, including restored map choices. */
import { useEffect } from 'react';
import { useCapabilitiesStore, type CapabilitiesState } from '@/stores/capabilities';
import { isOsLayer, type BaseLayer } from './baseLayers';

export const LICENCE_UNAVAILABLE = 'Not available on this installation due to licence terms';

export function sourceUnavailable(policy: CapabilitiesState, id: string): string | null {
  if (policy.error) return policy.error;
  if (!policy.loaded || policy.commercialUse === null)
    return 'Checking installation licence policy…';
  if (!policy.commercialUse || policy.sourceLicences[id]?.available) return null;
  return LICENCE_UNAVAILABLE;
}

export function basemapSources(layer: BaseLayer): string[] {
  return [
    'map:openfreemap',
    ...(['satellite', 'hybrid'].includes(layer) ? ['map:eox_s2cloudless'] : []),
    ...(isOsLayer(layer) ? ['map:os_maps'] : []),
  ];
}

export function basemapUnavailable(policy: CapabilitiesState, layer: BaseLayer): string | null {
  for (const source of basemapSources(layer)) {
    const reason = sourceUnavailable(policy, source);
    if (reason) return reason;
  }
  return isOsLayer(layer) && !policy.osMaps
    ? 'OS Maps is not configured on this installation.'
    : null;
}

export function mapSourceAllowed(id: string): boolean {
  return sourceUnavailable(useCapabilitiesStore.getState(), id) === null;
}

export function useMapSourcePolicy() {
  const policy = useCapabilitiesStore();
  useEffect(() => {
    void policy.load();
  }, [policy.load]);
  return policy;
}

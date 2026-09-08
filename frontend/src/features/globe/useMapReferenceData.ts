import { useEffect } from 'react';
import { useCapabilitiesStore } from '@/stores/capabilities';
import { useCountriesStore } from '@/stores/countries';
import type { BaseLayer } from '@/stores/globe';
import { isOsLayer } from './engine/baseLayers';

/** Load reference catalogues and reject a remembered map style unavailable on this server. */
export function useMapReferenceData(
  baseLayer: BaseLayer,
  setBaseLayer: (layer: BaseLayer) => void,
) {
  const osMaps = useCapabilitiesStore((state) => state.osMaps);
  const loaded = useCapabilitiesStore((state) => state.loaded);
  const loadCapabilities = useCapabilitiesStore((state) => state.load);
  const countries = useCountriesStore((state) => state.items);
  const countryByIso = useCountriesStore((state) => state.byIso);
  const countriesError = useCountriesStore((state) => state.error);
  const loadCountries = useCountriesStore((state) => state.load);
  useEffect(() => {
    void loadCapabilities();
  }, [loadCapabilities]);
  useEffect(() => {
    void loadCountries();
  }, [loadCountries]);
  useEffect(() => {
    if (loaded && !osMaps && isOsLayer(baseLayer)) setBaseLayer('dark');
  }, [baseLayer, loaded, osMaps, setBaseLayer]);
  return { osMaps, countries, countryByIso, countriesError };
}

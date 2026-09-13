import type { Country } from '@/lib/api/geoSchemas';
import type { useDashboardEvents } from './useDashboardEvents';
import { useCyberCountryContext } from './useCyberCountryContext';
import { useNewsCountryContext } from './useNewsCountryContext';

/** Country references share current source, time, quality and account scope. */
export function useReportingReferences(
  data: ReturnType<typeof useDashboardEvents>,
  countries: Record<string, Country>,
  visible: boolean,
  now: number,
) {
  const cyber = useCyberCountryContext(
    !data.hidden.includes('cyber') && visible,
    countries,
    data.country,
    data.windowHours,
    now,
    data.quality.filter,
  );
  const news = useNewsCountryContext(data.quality.filtered, countries, data.newsSnapshot.key);
  return { cyber, news };
}

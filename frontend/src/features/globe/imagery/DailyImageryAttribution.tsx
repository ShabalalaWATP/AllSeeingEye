/** Keeps the NASA credit, product and date visible on the map while the imagery is shown. */
import { useNow } from '@/lib/hooks/useNow';
import { dailyImageryProduct } from '@/lib/map/dailyImagery';

import { selectDailyImagery, useDailyImageryStore } from './dailyImageryStore';

const DATE_FORMAT = new Intl.DateTimeFormat('en-GB', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  timeZone: 'UTC',
});

export function formatImageryDate(date: string): string {
  const parsed = Date.parse(`${date}T00:00:00Z`);
  return Number.isFinite(parsed) ? DATE_FORMAT.format(parsed) : date;
}

export function GibsCredit() {
  return (
    <>
      Imagery from{' '}
      <a
        className="text-ember underline underline-offset-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ember"
        href="https://www.earthdata.nasa.gov/gibs"
        target="_blank"
        rel="noreferrer"
      >
        NASA GIBS
      </a>
      , part of NASA ESDIS. NASA imagery has no usage restrictions; credit NASA when you reuse it.
    </>
  );
}

export function DailyImageryAttribution() {
  const enabled = useDailyImageryStore((state) => state.enabled);
  const product = useDailyImageryStore((state) => state.product);
  const date = useDailyImageryStore((state) => state.date);
  const now = useNow();
  const imagery = selectDailyImagery({ enabled, product, date }, now);
  const details = imagery && dailyImageryProduct(imagery.product);
  if (!imagery || !details) return null;
  return (
    <p className="pointer-events-none absolute top-20 right-20 left-20 z-10 text-right text-2xs text-muted">
      <span className="pointer-events-auto inline-flex flex-wrap justify-end gap-x-1 rounded bg-black/80 px-2 py-1">
        <span>
          {details.label} for {formatImageryDate(imagery.date)}
        </span>
        <span aria-hidden="true">·</span>
        <a
          className="underline decoration-white/30 underline-offset-2 focus-visible:outline-2 focus-visible:outline-cyan"
          href="https://www.earthdata.nasa.gov/gibs"
          target="_blank"
          rel="noreferrer"
        >
          NASA GIBS
        </a>
      </span>
    </p>
  );
}

import { useMinuteClock } from './useMinuteClock';

export const WORLD_CLOCKS = [
  { city: 'London', zone: 'Europe/London' },
  { city: 'Kyiv', zone: 'Europe/Kyiv' },
  { city: 'Moscow', zone: 'Europe/Moscow' },
  { city: 'Beijing', zone: 'Asia/Shanghai' },
  { city: 'Seoul', zone: 'Asia/Seoul' },
  { city: 'Sydney', zone: 'Australia/Sydney' },
  { city: 'Washington DC', zone: 'America/New_York' },
] as const;

const formatters = WORLD_CLOCKS.map(({ zone }) => ({
  time: new Intl.DateTimeFormat('en-GB', {
    timeZone: zone,
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  }),
  date: new Intl.DateTimeFormat('en-GB', {
    timeZone: zone,
    weekday: 'short',
    day: '2-digit',
    month: 'short',
  }),
}));

export function WorldClocks() {
  const now = useMinuteClock();
  return (
    <section
      aria-label="World clocks"
      className="map-world-clocks pointer-events-none absolute inset-x-3 z-10 flex justify-center"
    >
      <dl className="pointer-events-auto grid max-w-full grid-cols-4 gap-x-2 gap-y-1.5 rounded-sm bg-black/75 px-2 py-1.5 text-center text-[9px] text-muted backdrop-blur-sm sm:px-3 sm:text-[10px] md:grid-cols-7 md:gap-x-3 xl:gap-x-6">
        {WORLD_CLOCKS.map((clock, index) => (
          <div key={clock.zone} className="flex flex-col items-center gap-0.5 xl:flex-row xl:gap-2">
            <dt>{clock.city}</dt>
            <dd>
              <time
                dateTime={new Date(now).toISOString()}
                title={`${formatters[index]?.date.format(now)} · ${clock.zone}`}
                aria-label={`${clock.city}: ${formatters[index]?.time.format(now)}, ${formatters[index]?.date.format(now)}`}
                className="font-mono text-[11px] sm:text-xs text-text/85 tabular-nums"
              >
                {formatters[index]?.time.format(now)}
              </time>
            </dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

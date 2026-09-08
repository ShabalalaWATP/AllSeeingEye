import { useMinuteClock } from './useMinuteClock';

export const WORLD_CLOCKS = [
  { city: 'London', zone: 'Europe/London' },
  { city: 'Kyiv', zone: 'Europe/Kyiv' },
  { city: 'Moscow', zone: 'Europe/Moscow' },
  { city: 'Beijing', zone: 'Asia/Shanghai' },
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
      className="pointer-events-none absolute inset-x-3 bottom-9 z-10 flex justify-center"
    >
      <dl className="pointer-events-auto grid grid-cols-4 gap-x-4 rounded-sm bg-black/75 px-3 py-1.5 text-[10px] text-muted backdrop-blur-sm sm:gap-x-6">
        {WORLD_CLOCKS.map((clock, index) => (
          <div key={clock.zone} className="flex flex-col items-center gap-0.5 sm:flex-row sm:gap-2">
            <dt>{clock.city}</dt>
            <dd>
              <time
                dateTime={new Date(now).toISOString()}
                title={`${formatters[index]?.date.format(now)} · ${clock.zone}`}
                aria-label={`${clock.city}: ${formatters[index]?.time.format(now)}, ${formatters[index]?.date.format(now)}`}
                className="font-mono text-xs text-text/85 tabular-nums"
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

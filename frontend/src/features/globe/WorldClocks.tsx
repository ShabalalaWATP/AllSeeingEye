import { useMinuteClock } from './useMinuteClock';

export const WORLD_CLOCKS = [
  { city: 'London', zone: 'Europe/London', code: 'UK' },
  { city: 'Berlin', zone: 'Europe/Berlin', code: 'DE' },
  { city: 'Moscow', zone: 'Europe/Moscow', code: 'RU' },
  { city: 'Tallinn', zone: 'Europe/Tallinn', code: 'EE' },
  { city: 'Beijing', zone: 'Asia/Shanghai', code: 'CN' },
  { city: 'Kyiv', zone: 'Europe/Kyiv', code: 'UA' },
  { city: 'Mumbai', zone: 'Asia/Kolkata', code: 'IN' },
  { city: 'Tokyo', zone: 'Asia/Tokyo', code: 'JP' },
  { city: 'Canberra', zone: 'Australia/Sydney', code: 'AU' },
  { city: 'Washington DC', zone: 'America/New_York', code: 'US' },
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
      className="absolute inset-x-3 bottom-9 z-10 overflow-hidden rounded-lg border border-white/15 bg-[#05090e]/95 text-text shadow-[0_0_35px_#0008] backdrop-blur-xl"
    >
      <div className="flex items-center justify-between border-b border-white/10 px-3 py-1.5 font-mono text-[9px] uppercase tracking-[0.2em] text-cyan/80">
        <span>World time</span>
        <span className="text-muted">24-hour · local dates · scroll for cities</span>
      </div>
      <div
        // Keyboard focus enables arrow-key scrolling of the city rail.
        // eslint-disable-next-line jsx-a11y/no-noninteractive-tabindex
        tabIndex={0}
        aria-label="City times, scroll horizontally"
        className="flex overflow-x-auto overscroll-x-contain focus-visible:outline-2 focus-visible:outline-cyan [scrollbar-width:thin]"
      >
        {WORLD_CLOCKS.map((clock, index) => (
          <div
            key={clock.zone}
            className="min-w-[106px] flex-1 border-r border-white/10 px-3 py-2 last:border-0 transition-colors hover:bg-cyan/5"
          >
            <div className="flex items-center justify-between gap-2 text-[10px] font-medium whitespace-nowrap">
              <span>{clock.city}</span>
              <span className="text-[8px] text-muted">{clock.code}</span>
            </div>
            <time
              dateTime={new Date(now).toISOString()}
              title={clock.zone}
              className="block font-mono text-xl leading-7 tracking-tight text-[#c9f7ff] tabular-nums"
            >
              {formatters[index]?.time.format(now)}
            </time>
            <div className="font-mono text-[9px] text-muted">
              {formatters[index]?.date.format(now)}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

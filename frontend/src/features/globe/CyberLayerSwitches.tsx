import { MapControlIcon } from './MapControlIcon';
import { useEventsStore } from '@/stores/events';
import { useGlobeStore } from '@/stores/globe';

/** The two map layers behind the Cyber control: collected records and GPS interference cells. */
export function CyberLayerSwitches({
  recordCount,
  interferenceCount,
}: {
  recordCount: number;
  interferenceCount: number;
}) {
  const hidden = useEventsStore((state) => state.hidden.includes('cyber'));
  const toggleCategory = useEventsStore((state) => state.toggleCategory);
  const interference = useGlobeStore((state) => state.interference);
  const toggleInterference = useGlobeStore((state) => state.toggleInterference);
  const rows = [
    {
      label: 'Cyber incidents',
      icon: 'cyber' as const,
      description: 'Ransomware claims, outage signals, advisories and reporting',
      count: recordCount,
      enabled: !hidden,
      toggle: () => toggleCategory('cyber'),
    },
    {
      label: 'GPS interference',
      icon: 'gnss' as const,
      description: 'Aircraft-reported navigation accuracy anomalies in 1° cells',
      count: interferenceCount,
      enabled: interference,
      toggle: toggleInterference,
    },
  ];
  return (
    <div role="group" aria-label="Cyber layers" className="space-y-2 p-2">
      {rows.map((row) => (
        <button
          key={row.label}
          type="button"
          role="switch"
          aria-label={`${row.label} ${row.count}`}
          aria-checked={row.enabled}
          onClick={row.toggle}
          className="flex min-h-14 w-full items-center gap-3 rounded-lg border border-line px-3 py-2 text-left text-sm transition-colors hover:bg-white/5 focus-visible:outline-2 focus-visible:outline-cyan"
        >
          <span className="text-cyan">
            <MapControlIcon name={row.icon} />
          </span>
          <span className="min-w-0 flex-1">
            <span className="block font-medium">{row.label}</span>
            <span className="mt-0.5 block text-[11px] leading-relaxed text-muted">
              {row.description} · {row.count.toLocaleString('en-GB')} loaded
            </span>
          </span>
          <span
            aria-hidden="true"
            className={`flex h-5 w-9 shrink-0 items-center rounded-full p-0.5 ${row.enabled ? 'bg-cyan/70' : 'bg-white/15'}`}
          >
            <span
              className={`h-4 w-4 rounded-full bg-white transition-transform ${row.enabled ? 'translate-x-4' : ''}`}
            />
          </span>
        </button>
      ))}
    </div>
  );
}

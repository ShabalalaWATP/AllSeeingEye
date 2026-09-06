import { BrandMark } from '@/components/brand/BrandMark';
import { Button } from '@/components/ui/Button';
import { useShellAlerts } from './useShellAlerts';
import { useGlobeStore } from '@/stores/globe';

const SHOWN = 3;

/** What the wall screen carries over the turning globe: the brand, an exit hint and live alerts. */
export function OpsRoomOverlay() {
  const lite = useGlobeStore((state) => state.lite);
  const alerts = useShellAlerts()?.items.filter((item) => item.acknowledged_at === null) ?? [];
  const setOpsRoom = useGlobeStore((state) => state.setOpsRoom);

  return (
    <>
      {alerts.length > 0 && (
        <aside
          aria-label="Unacknowledged alerts"
          className="pointer-events-none absolute top-3 right-3 z-20 flex w-80 max-w-[calc(100%-1.5rem)] flex-col gap-2"
        >
          {alerts.slice(0, SHOWN).map((item) => (
            <div
              key={item.id}
              className="rounded-card border border-critical/60 bg-ground/90 px-3 py-2 text-sm text-text shadow-lg"
            >
              <div className="font-medium">{item.title}</div>
              {item.summary !== '' && (
                <div className="mt-1 line-clamp-2 text-xs text-muted">{item.summary}</div>
              )}
            </div>
          ))}
          {alerts.length > SHOWN && (
            <div className="px-1 font-mono text-[11px] text-muted">
              {alerts.length - SHOWN} more on the warning page
            </div>
          )}
        </aside>
      )}
      <div className="absolute bottom-3 left-3 z-20 flex items-center gap-3">
        <BrandMark still={lite} />
        <Button
          variant="ghost"
          aria-label="Exit ops room"
          onClick={() => setOpsRoom(false)}
          className="min-h-11 font-mono text-[11px] uppercase tracking-[0.2em] text-muted"
        >
          Ops room · Esc to exit
        </Button>
      </div>
    </>
  );
}

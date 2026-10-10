/** Slow globe steps, including MapLibre's synchronous reduced-motion completion. */
import type { Map as MapLibreMap } from 'maplibre-gl';

export const SPIN_DEGREES = 15;
export const SPIN_STEP_MS = 30_000;

export class MapSpin {
  private enabled = false;
  private stepping = false;

  constructor(private readonly currentMap: () => MapLibreMap | null) {}

  set(enabled: boolean): void {
    if (this.enabled === enabled) return;
    this.enabled = enabled;
    if (enabled) this.step();
    else this.currentMap()?.stop();
  }

  step(): void {
    const map = this.currentMap();
    if (!map || !this.enabled) return;
    if (this.stepping) {
      this.enabled = false;
      return;
    }
    const center = map.getCenter();
    this.stepping = true;
    try {
      map.easeTo({
        center: [center.lng + SPIN_DEGREES, center.lat],
        duration: SPIN_STEP_MS,
        easing: (t: number) => t,
      });
    } finally {
      this.stepping = false;
    }
  }
}

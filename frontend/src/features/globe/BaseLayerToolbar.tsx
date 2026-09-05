import type { BaseLayer } from '@/stores/globe';

import { BASE_LAYER_OPTIONS } from './engine/baseLayers';

export interface BaseLayerToolbarProps {
  value: BaseLayer;
  /** Whether the server proxies Ordnance Survey tiles (it needs a key). */
  osAvailable: boolean;
  onChange: (layer: BaseLayer) => void;
}

/** Segmented choice of what to draw under the data. */
export function BaseLayerToolbar({ value, osAvailable, onChange }: BaseLayerToolbarProps) {
  const options = BASE_LAYER_OPTIONS.filter((option) => osAvailable || !option.needsOs);
  return (
    <div
      role="group"
      aria-label="Base layer"
      className="flex flex-wrap overflow-hidden rounded-md border border-line bg-surface/90 backdrop-blur"
    >
      {options.map((option) => {
        const active = option.id === value;
        return (
          <button
            key={option.id}
            type="button"
            aria-pressed={active}
            onClick={() => {
              onChange(option.id);
            }}
            className={`px-2 py-1 text-xs transition-colors ${
              active ? 'bg-surface-2 text-text' : 'text-muted hover:bg-surface-2 hover:text-text'
            }`}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}

import type { RfCalculatorPanelProps } from './RfCalculatorPanel';
export function RfPositions({
  origin,
  receiver,
  picking,
  onPick,
  onClearReceiver,
}: Pick<RfCalculatorPanelProps, 'origin' | 'receiver' | 'picking' | 'onPick' | 'onClearReceiver'>) {
  return (
    <>
      {onPick && (
        <div className="space-y-2 rounded border border-line bg-ground/50 p-3">
          <p className="font-mono uppercase tracking-wide text-muted">Position on map</p>
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              aria-pressed={picking === 'origin'}
              onClick={() => onPick(picking === 'origin' ? null : 'origin')}
              className="min-h-10 rounded border border-line px-2 text-cyan"
            >
              {origin ? 'Move transmitter' : 'Place transmitter'}
            </button>
            <button
              type="button"
              aria-pressed={picking === 'receiver'}
              onClick={() => onPick(picking === 'receiver' ? null : 'receiver')}
              className="min-h-10 rounded border border-line px-2 text-cyan"
            >
              {receiver ? 'Move receiver' : 'Add receiver'}
            </button>
          </div>
          {picking && (
            <p role="status" className="text-cyan">
              Click the map to place the {picking === 'origin' ? 'transmitter' : 'receiver'}. Select
              the button again to cancel.
            </p>
          )}
          {origin && (
            <p className="font-mono text-muted">
              TX {origin[1].toFixed(4)}, {origin[0].toFixed(4)}
            </p>
          )}
          {receiver && (
            <p className="font-mono text-muted">
              RX {receiver[1].toFixed(4)}, {receiver[0].toFixed(4)}
            </p>
          )}
          {receiver && onClearReceiver && (
            <button
              type="button"
              onClick={onClearReceiver}
              className="min-h-9 text-muted underline"
            >
              Remove receiver, keep transmitter
            </button>
          )}
          {origin && receiver && (
            <p className="text-muted">Path length follows the two map positions.</p>
          )}
        </div>
      )}
    </>
  );
}

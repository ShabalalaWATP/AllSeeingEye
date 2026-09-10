import type { RfCalculatorPanelProps } from './RfCalculatorPanel';
export function RfPositions({
  origin,
  receiver,
  picking,
  onPick,
  onClearReceiver,
  pathActive = true,
}: Pick<
  RfCalculatorPanelProps,
  'origin' | 'receiver' | 'picking' | 'onPick' | 'onClearReceiver'
> & { pathActive?: boolean }) {
  return (
    <>
      {onPick && (
        <div className="rf-positions">
          <div className="rf-stations">
            {(['origin', 'receiver'] as const).map((id) => {
              const point = id === 'origin' ? origin : receiver;
              const label =
                id === 'origin'
                  ? point
                    ? 'Move transmitter'
                    : 'Place transmitter'
                  : point
                    ? 'Move receiver'
                    : 'Add receiver';
              return (
                <button
                  key={id}
                  type="button"
                  aria-label={label}
                  aria-pressed={picking === id}
                  onClick={() => onPick(picking === id ? null : id)}
                  className="rf-station"
                >
                  <span className="rf-station-top">
                    <span className="rf-station-symbol" aria-hidden="true">
                      {id === 'origin' ? 'TX' : 'RX'}
                    </span>
                    <span className="rf-station-state">
                      {picking === id ? 'Placing' : point ? 'Located' : 'Not placed'}
                    </span>
                  </span>
                  <span className="rf-station-title">
                    {id === 'origin' ? 'Transmitter' : 'Receiver'}
                  </span>
                  <span className="rf-station-position">
                    {point
                      ? `${point[1].toFixed(4)}, ${point[0].toFixed(4)}`
                      : 'Select a point on the map'}
                  </span>
                  <span className="rf-station-action">
                    {picking === id ? 'Cancel placement' : label}
                    <span aria-hidden="true">↗</span>
                  </span>
                </button>
              );
            })}
          </div>
          {picking && (
            <p role="status" className="rf-placement-status">
              Click the map to place the {picking === 'origin' ? 'transmitter' : 'receiver'}. Select
              the button again to cancel.
            </p>
          )}
          {receiver && onClearReceiver && (
            <button type="button" onClick={onClearReceiver} className="rf-text-button">
              Remove receiver, keep transmitter
            </button>
          )}
          {origin && receiver && pathActive && (
            <p className="rf-help">Path length follows the two map positions.</p>
          )}
        </div>
      )}
    </>
  );
}

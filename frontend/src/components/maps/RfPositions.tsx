import { RfSiteEditor } from './RfSiteEditor';
import type { RfCalculatorPanelProps } from './rfCalculatorTypes';
export function RfPositions({
  siteNames = { origin: '', receiver: '' },
  interaction = 'click',
  onDragSite,
  onSetSite,
  onSwapSites,
  origin,
  receiver,
  picking,
  onPick,
  onClearReceiver,
  pathActive = true,
}: Pick<
  RfCalculatorPanelProps,
  | 'interaction'
  | 'onDragSite'
  | 'origin'
  | 'receiver'
  | 'picking'
  | 'onPick'
  | 'onClearReceiver'
  | 'siteNames'
  | 'onSetSite'
  | 'onSwapSites'
> & { pathActive?: boolean }) {
  return (
    <>
      {onSetSite && (
        <details className="mt-2">
          <summary>Enter precise sites</summary>
          <p className="rf-help">
            WGS84 latitude then longitude. Decimal degrees or degrees, minutes and seconds with
            hemisphere.
          </p>
          {(['origin', 'receiver'] as const).map((kind) => (
            <RfSiteEditor
              key={`${kind}:${String(kind === 'origin' ? origin : receiver)}:${siteNames[kind]}`}
              kind={kind}
              position={(kind === 'origin' ? origin : receiver) ?? null}
              name={siteNames[kind]}
              onSet={onSetSite}
            />
          ))}
        </details>
      )}
      {onDragSite && (
        <div className="flex flex-wrap gap-2">
          {(['origin', 'receiver'] as const).map((kind) => (
            <button
              key={kind}
              type="button"
              className="rf-secondary-button"
              disabled={!(kind === 'origin' ? origin : receiver)}
              aria-pressed={interaction === 'drag' && picking === kind}
              onClick={() =>
                interaction === 'drag' && picking === kind ? onPick?.(null) : onDragSite(kind)
              }
            >
              Drag {kind === 'origin' ? 'transmitter' : 'receiver'}
            </button>
          ))}
        </div>
      )}
      {onSwapSites && (
        <button
          className="rf-secondary-button"
          type="button"
          disabled={!origin || !receiver}
          onClick={onSwapSites}
        >
          Swap transmitter and receiver
        </button>
      )}
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
                    {siteNames[id].length > 0
                      ? siteNames[id]
                      : id === 'origin'
                        ? 'Transmitter'
                        : 'Receiver'}
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
              {interaction === 'drag'
                ? 'Drag the existing site marker to move the'
                : 'Click the map to place the'}{' '}
              {picking === 'origin' ? 'transmitter' : 'receiver'}. Select the button again to
              cancel.
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

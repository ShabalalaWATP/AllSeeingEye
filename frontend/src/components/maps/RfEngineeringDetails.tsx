import type { ReactNode } from 'react';

/** Detailed figures stay available without being the first thing a new user must interpret. */
export function RfEngineeringDetails({ children }: { children: ReactNode }) {
  return (
    <details className="rf-disclosure">
      <summary>Engineering details</summary>
      <div className="rf-disclosure-body space-y-4">
        <details className="rounded border border-line p-3 text-xs">
          <summary className="cursor-pointer">Explain the terms</summary>
          <dl className="mt-3 space-y-3 text-muted">
            <div>
              <dt className="font-medium text-text">TX / RX</dt>
              <dd>The transmitter sends the signal. The receiver listens for it.</dd>
            </div>
            <div>
              <dt className="font-medium text-text">Receive power (dBm)</dt>
              <dd>
                The modelled signal strength at the receiver. A less negative value is stronger: −70
                dBm is stronger than −90 dBm.
              </dd>
            </div>
            <div>
              <dt className="font-medium text-text">Receiver sensitivity</dt>
              <dd>
                The minimum signal level entered for your receiver and operating mode. Check it
                against the equipment specification.
              </dd>
            </div>
            <div>
              <dt className="font-medium text-text">Signal margin and reserve (dB)</dt>
              <dd>
                Margin is the difference between the estimated signal and the receiver's required
                level. The planning reserve is an extra allowance you choose. A negative margin
                after reserve falls short of that allowance; it is not a success percentage.
              </dd>
            </div>
            <div>
              <dt className="font-medium text-text">Fresnel clearance</dt>
              <dd>
                Radio waves need clear space around the direct path too. An obstacle near that path
                can affect the signal even when it does not cross the centre line.
              </dd>
            </div>
            <div>
              <dt className="font-medium text-text">Diffraction loss</dt>
              <dd>
                The model's estimate of signal reduction as waves travel around an obstruction. An
                obstructed direct path does not necessarily mean no reception.
              </dd>
            </div>
            <div>
              <dt className="font-medium text-text">Antenna height (AGL)</dt>
              <dd>Height above local ground. This differs from elevation above sea level.</dd>
            </div>
            <div>
              <dt className="font-medium text-text">Terrain grid (DEM)</dt>
              <dd>
                The elevation data used for ground heights. Grid spacing describes how far apart
                source points are, not how accurate their heights are.
              </dd>
            </div>
          </dl>
        </details>
        {children}
      </div>
    </details>
  );
}

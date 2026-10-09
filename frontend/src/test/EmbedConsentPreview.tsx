/** Local-only fixture entry. Intercept all non-loopback traffic before navigating here. */
import { useState } from 'react';
import { createRoot } from 'react-dom/client';

import '@/styles/theme.css';
import { EmbedPrivacyPreferences } from '@/components/privacy/EmbedPrivacyPreferences';
import { Button } from '@/components/ui/Button';
import { MarketWorkspace } from '@/features/economy/MarketWorkspace';
import { CameraStream } from '@/features/globe/cameras/CameraStream';
import type { Camera } from '@/lib/api/cameras';
import { useAuthStore } from '@/stores/auth';
import { plainUser } from './fixtures';

const camera: Camera = {
  id: 'youtube-fixture',
  provider: 'fixture',
  title: 'YouTube fixture',
  latitude: 0,
  longitude: 0,
  coordinate_precision: 'approximate',
  snapshot_url: null,
  captured_at: null,
  external_url: null,
  source_url: 'https://www.youtube.com/',
  attribution: 'Local fixture',
  stream_type: 'iframe',
  stream_url: 'https://www.youtube.com/embed/UemFRPrl1hk',
};

function Preview() {
  const [selection, setSelection] = useState(0);
  return (
    <main className="mx-auto max-w-4xl space-y-8 p-5 text-text">
      <h1 className="text-2xl font-semibold">External media consent verification</h1>
      <p>Local fixtures. All provider responses must be intercepted by the verification browser.</p>
      <MarketWorkspace region="US" />
      <section aria-label="YouTube camera" className="space-y-3">
        <h2 className="text-xl font-semibold">YouTube camera</h2>
        <Button onClick={() => setSelection((value) => value + 1)}>Select another camera</Button>
        <CameraStream camera={{ ...camera, id: `youtube-${selection}` }} />
      </section>
      <section aria-label="IPCamLive camera" className="space-y-3">
        <h2 className="text-xl font-semibold">IPCamLive camera</h2>
        <CameraStream
          camera={{
            ...camera,
            id: 'ipcamlive-fixture',
            title: 'IPCamLive fixture',
            stream_url: 'https://ipcamlive.com/player/player.php?alias=fixture',
          }}
        />
      </section>
      <EmbedPrivacyPreferences />
    </main>
  );
}

if (!import.meta.env.DEV) throw new Error('Consent preview is development-only');
// Synthetic identity only. This fixture does not bootstrap, issue credentials or call the API.
useAuthStore.setState({ status: 'authenticated', user: plainUser });
const root = document.getElementById('root');
if (!root) throw new Error('Missing preview root');
createRoot(root).render(<Preview />);

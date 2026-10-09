import hosts from './cameraMediaHosts.json';
import { isCameraStreamUrl } from './cameras';
import type { EmbedProvider } from '@/lib/embedProviders';

/** Legacy catalogue URLs are accepted as input, but never rendered as frame destinations. */
export function cameraEmbed(value: string | null): { url: string; provider: EmbedProvider } | null {
  if (!value || !isCameraStreamUrl(value, true)) return null;
  const url = new URL(value);
  if (url.hostname === 'www.youtube.com') url.hostname = 'www.youtube-nocookie.com';
  if (!hosts.frames.includes(url.hostname)) return null;
  if (url.hostname === 'www.youtube-nocookie.com') {
    if (!/^\/embed\/[A-Za-z0-9_-]{11}$/.test(url.pathname)) return null;
    return { url: url.href, provider: 'youtube' };
  }
  if (url.hostname === 'ipcamlive.com' && url.pathname === '/player/player.php')
    return { url: url.href, provider: 'ipcamlive' };
  return null;
}

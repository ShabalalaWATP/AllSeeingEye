import { registerPush, removePush } from '@/lib/api/webPush';
import type { PushDevice } from '@/lib/api/webPush';

export function pushSupported(): boolean {
  return (
    window.isSecureContext &&
    'serviceWorker' in navigator &&
    'PushManager' in window &&
    'Notification' in window
  );
}

export async function endpointHash(subscription: PushSubscription): Promise<string> {
  const digest = await crypto.subtle.digest(
    'SHA-256',
    new TextEncoder().encode(subscription.endpoint),
  );
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, '0')).join('');
}

export async function currentPush(): Promise<PushSubscription | null> {
  if (!pushSupported()) return null;
  const registration = await navigator.serviceWorker.getRegistration('/');
  return (await registration?.pushManager.getSubscription()) ?? null;
}

export async function enablePush(publicKey: string, devices: PushDevice[]): Promise<PushDevice> {
  if (!pushSupported()) throw new Error('Push is unsupported.');
  // This call must occur directly in the button's user gesture, before network work.
  if ((await Notification.requestPermission()) !== 'granted')
    throw new Error('Push permission was not granted.');
  const registration = await navigator.serviceWorker.register('/push-worker.js', { scope: '/' });
  await navigator.serviceWorker.ready;
  const old = await registration.pushManager.getSubscription();
  if (old) {
    const hash = await endpointHash(old);
    const previous = devices.find((device) => device.endpoint_hash === hash);
    if (previous) await removePush(previous.id);
    await old.unsubscribe();
  }
  const decoded = atob(publicKey.replace(/-/g, '+').replace(/_/g, '/'));
  const key = Uint8Array.from(decoded, (value) => value.charCodeAt(0));
  const subscription = await registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: key,
  });
  const json = subscription.toJSON();
  try {
    if (!json.keys?.p256dh || !json.keys.auth)
      throw new Error('Browser returned incomplete push keys.');
    return await registerPush({
      endpoint: subscription.endpoint,
      p256dh: json.keys.p256dh,
      auth: json.keys.auth,
    });
  } catch (error) {
    await subscription.unsubscribe();
    throw error;
  }
}

export async function disablePush(device: PushDevice): Promise<void> {
  await removePush(device.id);
  const subscription = await currentPush();
  if (subscription && (await endpointHash(subscription)) === device.endpoint_hash)
    await subscription.unsubscribe();
}

export async function clearBrowserPush(): Promise<void> {
  const subscription = await currentPush();
  if (subscription) await subscription.unsubscribe();
}

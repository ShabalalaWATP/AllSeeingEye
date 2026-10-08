import { registerPush, removePush } from '@/lib/api/webPush';
import type { PushDevice } from '@/lib/api/webPush';
import { readStored, safeLocalStorage, writeStored } from '@/lib/safeStorage';

/** Which account opted this browser in, and the endpoint hash it registered. */
export interface PushRecord {
  owner: string;
  hash: string;
}
const RECORD_KEY = 'ase-push-device';

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

export function pushRecord(): PushRecord | null {
  try {
    const value = JSON.parse(readStored(RECORD_KEY) ?? 'null') as Partial<PushRecord> | null;
    return typeof value?.owner === 'string' && typeof value.hash === 'string'
      ? { owner: value.owner, hash: value.hash }
      : null;
  } catch {
    return null;
  }
}

export function rememberPush(owner: string, hash: string): void {
  writeStored(RECORD_KEY, JSON.stringify({ owner, hash }));
}

function forgetPush(): void {
  safeLocalStorage.removeItem(RECORD_KEY);
}

export function applicationServerKey(publicKey: string) {
  const decoded = atob(publicKey.replace(/-/g, '+').replace(/_/g, '/'));
  return Uint8Array.from(decoded, (value) => value.charCodeAt(0));
}

/** Send only the endpoint and its keys; the caller decides what a failure discards. */
export function registerSubscription(subscription: PushSubscription): Promise<PushDevice> {
  const json = subscription.toJSON();
  if (!json.keys?.p256dh || !json.keys.auth)
    return Promise.reject(new Error('Browser returned incomplete push keys.'));
  return registerPush({
    endpoint: subscription.endpoint,
    p256dh: json.keys.p256dh,
    auth: json.keys.auth,
  });
}

export async function currentPush(): Promise<PushSubscription | null> {
  if (!pushSupported()) return null;
  const registration = await navigator.serviceWorker.getRegistration('/');
  return (await registration?.pushManager.getSubscription()) ?? null;
}

export async function enablePush(
  publicKey: string,
  devices: PushDevice[],
  owner: string,
): Promise<PushDevice> {
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
  const subscription = await registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: applicationServerKey(publicKey),
  });
  try {
    const device = await registerSubscription(subscription);
    rememberPush(owner, device.endpoint_hash);
    return device;
  } catch (error) {
    await subscription.unsubscribe();
    throw error;
  }
}

export async function disablePush(device: PushDevice): Promise<void> {
  await removePush(device.id);
  const subscription = await currentPush();
  if (subscription && (await endpointHash(subscription)) === device.endpoint_hash) {
    forgetPush();
    await subscription.unsubscribe();
  }
}

export async function clearBrowserPush(): Promise<void> {
  forgetPush();
  const subscription = await currentPush();
  if (subscription) await subscription.unsubscribe();
}

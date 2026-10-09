/**
 * The push service can replace or expire a browser's subscription at any time. The worker
 * subscribes again where it can but holds no credentials, so the signed-in app registers
 * the replacement: on load, and at once when the worker reports a change to an open window.
 * Only the account that opted this browser in may claim it, and a device it removed stays
 * removed because its subscription has not changed.
 */
import { getPushSettings, removePush } from '@/lib/api/webPush';

import {
  applicationServerKey,
  endpointHash,
  pushRecord,
  pushSupported,
  registerSubscription,
  rememberPush,
} from './browserPush';

export const PUSH_CHANGED_MESSAGE = 'push-subscription-changed';

/** Resolves true when a replacement subscription was registered for `owner`. */
export async function renewPush(owner: string): Promise<boolean> {
  const record = pushRecord();
  if (record?.owner !== owner || !pushSupported() || Notification.permission !== 'granted')
    return false;
  const registration = await navigator.serviceWorker.getRegistration('/');
  if (!registration) return false;
  const current = await registration.pushManager.getSubscription();
  if (current && (await endpointHash(current)) === record.hash) return false;
  const settings = await getPushSettings();
  if (!settings.public_key) return false;
  const subscription =
    current ??
    (await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: applicationServerKey(settings.public_key),
    }));
  // Signing out meanwhile forgets the record; never register for a session that has gone.
  if (pushRecord()?.owner !== owner) return false;
  const device = await registerSubscription(subscription);
  rememberPush(owner, device.endpoint_hash);
  // The replaced endpoint no longer delivers. The server also prunes it on its next send.
  const replaced = settings.devices.find((item) => item.endpoint_hash === record.hash);
  if (replaced && replaced.id !== device.id) await removePush(replaced.id);
  return true;
}

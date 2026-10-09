/*
 * Push, click and subscription renewal only. No fetch handler, API cache or background
 * authentication: the signed-in app registers a renewed subscription with the server.
 */
const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

self.addEventListener('push', (event) => {
  const id = event.data?.text() ?? '';
  if (!uuidPattern.test(id)) return;
  event.waitUntil(
    self.registration.showNotification('New alert', {
      body: 'Open the app to view this alert securely.',
      icon: '/brand/eye-192.png',
      tag: id,
      data: { id },
    }),
  );
});

/* Reuse an open app window when there is one, rather than opening another each time. */
async function openAlert(href) {
  const windows = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
  const existing = windows.find((client) => new URL(client.url).origin === self.location.origin);
  if (!existing) return self.clients.openWindow(href);
  const focused = await existing.focus();
  try {
    return (await focused.navigate(href)) ?? focused;
  } catch {
    // An uncontrolled window cannot be navigated from here; open the alert separately.
    return self.clients.openWindow(href);
  }
}

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const id = event.notification.data?.id;
  if (typeof id !== 'string' || !uuidPattern.test(id)) return;
  const target = new URL(`/warning?alert=${encodeURIComponent(id)}`, self.location.origin);
  event.waitUntil(openAlert(target.href));
});

/*
 * The push service replaced or expired the subscription. Subscribe again with the same
 * application server key when the browser has not already done so, then tell open app
 * windows. The app compares the browser subscription with the one it registered and
 * registers the replacement on its next load, or at once if a window is open.
 */
async function renewSubscription(event) {
  const key = event.oldSubscription?.options?.applicationServerKey;
  const current = event.newSubscription ?? (await self.registration.pushManager.getSubscription());
  if (!current && key)
    await self.registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: key,
    });
  const windows = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
  for (const client of windows) client.postMessage({ type: 'push-subscription-changed' });
}

self.addEventListener('pushsubscriptionchange', (event) => {
  event.waitUntil(renewSubscription(event));
});

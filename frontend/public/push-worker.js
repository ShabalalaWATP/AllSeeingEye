/* Push and click handling only. No fetch handler, API cache or background authentication. */
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

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const id = event.notification.data?.id;
  if (typeof id !== 'string' || !uuidPattern.test(id)) return;
  const target = new URL(`/warning?alert=${encodeURIComponent(id)}`, self.location.origin);
  event.waitUntil(self.clients.openWindow(target.href));
});

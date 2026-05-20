/// <reference lib="webworker" />

/**
 * Service Worker for Push Notifications
 * Handles incoming push events and notification clicks
 */

self.addEventListener("push", (event) => {
  if (!event.data) return;

  try {
    const data = event.data.json();
    const options = {
      body: data.body || "",
      icon: data.icon || "/octane-o.svg",
      badge: data.badge || "/octane-o.svg",
      tag: data.tag || "octane-notification",
      data: {
        url: data.url || "/",
      },
      vibrate: [200, 100, 200],
      requireInteraction: true,
    };

    event.waitUntil(
      self.registration.showNotification(data.title || "Octane", options)
    );
  } catch (err) {
    console.error("[sw-push] Failed to parse push data:", err);
  }
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();

  const url = event.notification.data?.url || "/";

  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((clientList) => {
      // Try to focus an existing window
      for (const client of clientList) {
        if (client.url.includes(self.location.origin) && "focus" in client) {
          client.navigate(url);
          return client.focus();
        }
      }
      // Open a new window if none exists
      if (self.clients.openWindow) {
        return self.clients.openWindow(url);
      }
    })
  );
});

// Handle notification close
self.addEventListener("notificationclose", (event) => {
  // Could log analytics here if needed
  console.log("[sw-push] Notification dismissed:", event.notification.tag);
});

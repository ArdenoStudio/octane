import { useState, useEffect, useCallback } from "react";
import { api } from "../lib/api";

type PushPermission = "default" | "granted" | "denied" | "unsupported";

interface PushSubscriptionState {
  permission: PushPermission;
  subscription: PushSubscription | null;
  isSupported: boolean;
  isLoading: boolean;
  error: string | null;
}

/**
 * Converts a base64 string to Uint8Array for VAPID key
 */
function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}

export function usePushNotifications() {
  const [state, setState] = useState<PushSubscriptionState>({
    permission: "default",
    subscription: null,
    isSupported: false,
    isLoading: true,
    error: null,
  });

  const isSupported =
    typeof window !== "undefined" &&
    "serviceWorker" in navigator &&
    "PushManager" in window &&
    "Notification" in window;

  // Check initial state
  useEffect(() => {
    if (!isSupported) {
      setState((prev) => ({
        ...prev,
        permission: "unsupported",
        isSupported: false,
        isLoading: false,
      }));
      return;
    }

    const checkState = async () => {
      try {
        const permission = Notification.permission as PushPermission;
        let subscription: PushSubscription | null = null;

        const registration = await navigator.serviceWorker.ready;
        subscription = await registration.pushManager.getSubscription();

        setState({
          permission,
          subscription,
          isSupported: true,
          isLoading: false,
          error: null,
        });
      } catch (err) {
        setState((prev) => ({
          ...prev,
          isLoading: false,
          error: err instanceof Error ? err.message : "Failed to check push state",
        }));
      }
    };

    checkState();
  }, [isSupported]);

  // Register service worker for push
  const registerServiceWorker = useCallback(async (): Promise<ServiceWorkerRegistration> => {
    // First, try to get existing registration
    const existingReg = await navigator.serviceWorker.getRegistration("/sw-push.js");
    if (existingReg) {
      return existingReg;
    }

    // Register new service worker
    const registration = await navigator.serviceWorker.register("/sw-push.js", {
      scope: "/",
    });

    // Wait for it to be ready
    await navigator.serviceWorker.ready;
    return registration;
  }, []);

  // Subscribe to push notifications
  const subscribe = useCallback(
    async (alertId: number): Promise<PushSubscription | null> => {
      if (!isSupported) {
        setState((prev) => ({ ...prev, error: "Push notifications not supported" }));
        return null;
      }

      setState((prev) => ({ ...prev, isLoading: true, error: null }));

      try {
        // Get VAPID public key from backend
        const { public_key: vapidKey } = await fetch(`${api.apiBase}/v1/push/vapid-key`).then(
          (r) => {
            if (!r.ok) throw new Error("Push not configured on server");
            return r.json();
          }
        );

        // Request notification permission
        const permission = await Notification.requestPermission();
        if (permission !== "granted") {
          setState((prev) => ({
            ...prev,
            permission: permission as PushPermission,
            isLoading: false,
            error: "Permission denied",
          }));
          return null;
        }

        // Register service worker and subscribe
        const registration = await registerServiceWorker();
        const subscription = await registration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: urlBase64ToUint8Array(vapidKey),
        });

        // Send subscription to backend
        const p256dh = subscription.getKey("p256dh");
        const auth = subscription.getKey("auth");

        if (!p256dh || !auth) {
          throw new Error("Failed to get subscription keys");
        }

        await fetch(`${api.apiBase}/v1/push/subscribe`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            alert_id: alertId,
            endpoint: subscription.endpoint,
            keys: {
              p256dh: btoa(String.fromCharCode(...new Uint8Array(p256dh))),
              auth: btoa(String.fromCharCode(...new Uint8Array(auth))),
            },
          }),
        }).then((r) => {
          if (!r.ok) throw new Error("Failed to register subscription");
        });

        setState({
          permission: "granted",
          subscription,
          isSupported: true,
          isLoading: false,
          error: null,
        });

        return subscription;
      } catch (err) {
        const message = err instanceof Error ? err.message : "Failed to subscribe";
        setState((prev) => ({
          ...prev,
          isLoading: false,
          error: message,
        }));
        return null;
      }
    },
    [isSupported, registerServiceWorker]
  );

  // Unsubscribe from push notifications
  const unsubscribe = useCallback(async (): Promise<boolean> => {
    if (!state.subscription) return true;

    setState((prev) => ({ ...prev, isLoading: true, error: null }));

    try {
      // Unsubscribe from browser
      await state.subscription.unsubscribe();

      // Remove from backend
      await fetch(`${api.apiBase}/v1/push/unsubscribe`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ endpoint: state.subscription.endpoint }),
      });

      setState((prev) => ({
        ...prev,
        subscription: null,
        isLoading: false,
        error: null,
      }));

      return true;
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to unsubscribe";
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: message,
      }));
      return false;
    }
  }, [state.subscription]);

  // Send test notification
  const sendTest = useCallback(async (): Promise<boolean> => {
    if (!state.subscription) return false;

    try {
      const p256dh = state.subscription.getKey("p256dh");
      const auth = state.subscription.getKey("auth");

      if (!p256dh || !auth) return false;

      const response = await fetch(`${api.apiBase}/v1/push/test`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          endpoint: state.subscription.endpoint,
          keys: {
            p256dh: btoa(String.fromCharCode(...new Uint8Array(p256dh))),
            auth: btoa(String.fromCharCode(...new Uint8Array(auth))),
          },
        }),
      });

      return response.ok;
    } catch {
      return false;
    }
  }, [state.subscription]);

  return {
    ...state,
    subscribe,
    unsubscribe,
    sendTest,
  };
}

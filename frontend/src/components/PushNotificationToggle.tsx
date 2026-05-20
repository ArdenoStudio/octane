import { RiBellLine, RiBellFill } from "@remixicon/react";
import { usePushNotifications } from "../hooks/usePushNotifications";
import { cn } from "../lib/utils";

interface PushNotificationToggleProps {
  alertId?: number;
  enabled: boolean;
  onToggle: (enabled: boolean) => void;
  className?: string;
}

export function PushNotificationToggle({
  alertId,
  enabled,
  onToggle,
  className,
}: PushNotificationToggleProps) {
  const { isSupported, permission, isLoading, subscribe, unsubscribe, error } =
    usePushNotifications();

  if (!isSupported) {
    return null;
  }

  const handleToggle = async () => {
    if (enabled) {
      // Turning off
      await unsubscribe();
      onToggle(false);
    } else {
      // Turning on - need alertId
      if (!alertId) {
        // Just toggle the state, actual subscription happens after alert creation
        onToggle(true);
        return;
      }
      const subscription = await subscribe(alertId);
      if (subscription) {
        onToggle(true);
      }
    }
  };

  const isDenied = permission === "denied";

  return (
    <div className={cn("flex items-center gap-3", className)}>
      <button
        type="button"
        onClick={handleToggle}
        disabled={isLoading || isDenied}
        className={cn(
          "flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
          enabled
            ? "bg-amber-100 text-amber-800 hover:bg-amber-200"
            : "bg-ink-900 text-ink-400 hover:bg-ink-800 hover:text-ink-300",
          (isLoading || isDenied) && "cursor-not-allowed opacity-50"
        )}
        aria-pressed={enabled}
      >
        {enabled ? (
          <RiBellFill className="h-4 w-4" />
        ) : (
          <RiBellLine className="h-4 w-4" />
        )}
        <span>{enabled ? "Push on" : "Push off"}</span>
      </button>
      {isDenied && (
        <span className="text-xs text-red-500">
          Notifications blocked. Enable in browser settings.
        </span>
      )}
      {error && !isDenied && (
        <span className="text-xs text-red-500">{error}</span>
      )}
    </div>
  );
}

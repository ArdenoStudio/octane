import { useState, useEffect } from "react";
import { RiWifiOffLine } from "@remixicon/react";

export function OfflineIndicator() {
  const [isOnline, setIsOnline] = useState(
    typeof navigator !== "undefined" ? navigator.onLine : true
  );
  const [showBanner, setShowBanner] = useState(false);

  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      // Show "back online" message briefly
      setShowBanner(true);
      setTimeout(() => setShowBanner(false), 3000);
    };

    const handleOffline = () => {
      setIsOnline(false);
      setShowBanner(true);
    };

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  if (!showBanner) return null;

  return (
    <div
      className={`fixed left-0 right-0 top-0 z-50 flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium transition-all duration-300 ${
        isOnline
          ? "bg-emerald-500 text-white"
          : "bg-amber-500 text-amber-950"
      }`}
    >
      {isOnline ? (
        <>Back online</>
      ) : (
        <>
          <RiWifiOffLine className="h-4 w-4" />
          <span>You&apos;re offline — showing cached data</span>
        </>
      )}
    </div>
  );
}

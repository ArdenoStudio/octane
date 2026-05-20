import { RiDownload2Line, RiCloseLine } from "@remixicon/react";
import { useInstallPrompt } from "../hooks/useInstallPrompt";

export function InstallPrompt() {
  const { isInstallable, promptInstall, dismiss } = useInstallPrompt();

  if (!isInstallable) return null;

  return (
    <div className="fixed bottom-4 left-4 right-4 z-50 mx-auto max-w-md animate-in slide-in-from-bottom-4 duration-300 sm:left-auto sm:right-4">
      <div className="flex items-center gap-3 rounded-xl border border-amber-200/50 bg-gradient-to-r from-amber-50 to-orange-50 p-4 shadow-lg shadow-amber-500/10">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-amber-500 text-white">
          <RiDownload2Line className="h-5 w-5" />
        </div>
        <div className="flex-1">
          <p className="text-sm font-semibold text-amber-900">Install Octane</p>
          <p className="text-xs text-amber-700">
            Get instant access to fuel prices from your home screen
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={promptInstall}
            className="rounded-lg bg-amber-500 px-3 py-1.5 text-sm font-semibold text-white transition-colors hover:bg-amber-600"
          >
            Install
          </button>
          <button
            onClick={dismiss}
            className="rounded-lg p-1.5 text-amber-600 transition-colors hover:bg-amber-100"
            aria-label="Dismiss"
          >
            <RiCloseLine className="h-5 w-5" />
          </button>
        </div>
      </div>
    </div>
  );
}

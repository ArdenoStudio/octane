import { useEffect, useState } from "react";

interface Props {
  show: boolean;
}

export function PageLoader({ show }: Props) {
  const [mounted, setMounted] = useState(true);

  useEffect(() => {
    if (!show) {
      const t = setTimeout(() => setMounted(false), 550);
      return () => clearTimeout(t);
    }
  }, [show]);

  if (!mounted) return null;

  return (
    <div
      className="fixed inset-0 z-[9999] flex items-center justify-center bg-white"
      style={{
        opacity: show ? 1 : 0,
        transition: "opacity 0.5s cubic-bezier(0.4, 0, 0.2, 1)",
        pointerEvents: show ? "auto" : "none",
      }}
    >
      <div className="relative flex items-center justify-center">
        {/* Faint full ring */}
        <div className="absolute h-[72px] w-[72px] rounded-full border-[2.5px] border-zinc-100" />

        {/* Spinning amber arc */}
        <div
          className="absolute h-[72px] w-[72px] rounded-full border-[2.5px] border-transparent"
          style={{
            borderTopColor: "#f59e0b",
            borderRightColor: "#f59e0b",
            animation: "octane-spin 0.9s cubic-bezier(0.4, 0, 0.2, 1) infinite",
          }}
        />

        {/* Logo — subtle pulse */}
        <img
          src="/octane-o.svg"
          alt="Octane"
          className="h-9 w-9"
          style={{
            animation: "octane-pulse 1.8s ease-in-out infinite",
          }}
        />
      </div>
    </div>
  );
}

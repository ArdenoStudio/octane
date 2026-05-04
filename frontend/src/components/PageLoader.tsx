import { useEffect, useState } from "react";

interface Props {
  show: boolean;
}

export function PageLoader({ show }: Props) {
  const [mounted, setMounted] = useState(true);

  useEffect(() => {
    if (!show) {
      const t = setTimeout(() => setMounted(false), 650);
      return () => clearTimeout(t);
    }
  }, [show]);

  if (!mounted) return null;

  return (
    <div
      className="fixed inset-0 z-[9999] flex flex-col items-center justify-center"
      style={{
        background:
          "radial-gradient(700px 380px at 50% 36%, rgba(245,158,11,0.09), transparent 60%), #fafaf9",
        opacity: show ? 1 : 0,
        transition: "opacity 0.6s cubic-bezier(0.4, 0, 0.2, 1)",
        pointerEvents: show ? "auto" : "none",
      }}
    >
      <div className="flex flex-col items-center">
        {/* Wordmark */}
        <img
          src="/octane-logo-nav.svg"
          alt="Octane"
          style={{
            width: 148,
            height: "auto",
            display: "block",
            animation: "octane-enter 0.55s cubic-bezier(0.0,0.0,0.2,1) both",
          }}
        />

        {/* Indeterminate shimmer bar */}
        <div
          style={{
            position: "relative",
            width: 136,
            height: 1.5,
            borderRadius: 99,
            background: "rgba(245,158,11,0.14)",
            overflow: "hidden",
            marginTop: 22,
            animation: "octane-enter 0.55s cubic-bezier(0.0,0.0,0.2,1) 0.15s both",
          }}
        >
          <div
            style={{
              position: "absolute",
              top: 0,
              bottom: 0,
              left: 0,
              width: "42%",
              background:
                "linear-gradient(90deg, transparent, #f59e0b 50%, transparent)",
              borderRadius: 99,
              animation: "octane-bar 1.6s cubic-bezier(0.4, 0, 0.6, 1) infinite",
            }}
          />
        </div>
      </div>

      {/* Byline */}
      <p
        className="absolute bottom-8 font-mono text-[10px] tracking-[0.06em] text-ink-600"
        style={{
          animation: "octane-enter 0.8s cubic-bezier(0.0,0.0,0.2,1) 0.35s both",
          opacity: 0.4,
        }}
      >
        © 2026 Built by Ardeno
      </p>
    </div>
  );
}

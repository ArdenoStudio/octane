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
      {/* Spinner — enters first */}
      <div
        className="relative flex items-center justify-center"
        style={{ animation: "octane-enter 0.5s cubic-bezier(0.0,0.0,0.2,1) both" }}
      >
        {/* Soft bloom */}
        <div
          className="absolute rounded-full"
          style={{
            width: 84,
            height: 84,
            background:
              "radial-gradient(circle, rgba(245,158,11,0.13) 0%, transparent 68%)",
            animation: "octane-bloom 2.6s ease-in-out infinite",
          }}
        />
        {/* Comet-tail arc via conic-gradient + ring mask */}
        <div
          style={{
            width: 54,
            height: 54,
            borderRadius: "50%",
            background:
              "conic-gradient(from 0deg, transparent 0%, rgba(245,158,11,0.08) 50%, #f59e0b 86%, transparent 100%)",
            WebkitMask:
              "radial-gradient(farthest-side, transparent calc(100% - 2px), #000 calc(100% - 2px))",
            mask: "radial-gradient(farthest-side, transparent calc(100% - 2px), #000 calc(100% - 2px))",
            animation: "octane-spin 1.1s linear infinite",
          }}
        />
      </div>

      {/* Wordmark — enters slightly after */}
      <img
        src="/octane-logo-nav.svg"
        alt="Octane"
        style={{
          width: 148,
          height: "auto",
          display: "block",
          marginTop: 28,
          animation: "octane-enter 0.6s cubic-bezier(0.0,0.0,0.2,1) 0.2s both",
        }}
      />

      {/* Byline */}
      <p
        className="absolute bottom-8 font-mono text-[10px] tracking-[0.06em] text-ink-600"
        style={{
          animation: "octane-enter 0.8s cubic-bezier(0.0,0.0,0.2,1) 0.4s both",
          opacity: 0.4,
        }}
      >
        © 2026 Built by Ardeno
      </p>
    </div>
  );
}

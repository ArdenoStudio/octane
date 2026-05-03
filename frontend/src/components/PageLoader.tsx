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

  // r=34 → circumference ≈ 213.6 — 120° arc ≈ 71, gap ≈ 143
  return (
    <div
      className="fixed inset-0 z-[9999] flex flex-col items-center justify-center"
      style={{
        background:
          "radial-gradient(900px 500px at 50% 40%, rgba(245,158,11,0.07), transparent 65%), #ffffff",
        opacity: show ? 1 : 0,
        transition: "opacity 0.6s cubic-bezier(0.4, 0, 0.2, 1)",
        pointerEvents: show ? "auto" : "none",
      }}
    >
      <div
        style={{
          animation: "octane-enter 0.45s cubic-bezier(0.0, 0.0, 0.2, 1) both",
        }}
        className="flex flex-col items-center gap-7"
      >
        {/* Standalone spinning arc */}
        <div className="relative flex items-center justify-center">
          <div
            className="absolute rounded-full"
            style={{
              width: 72,
              height: 72,
              background:
                "radial-gradient(circle, rgba(245,158,11,0.13) 0%, transparent 70%)",
              animation: "octane-bloom 2.2s ease-in-out infinite",
            }}
          />
          <svg width="52" height="52" viewBox="0 0 52 52">
            <circle cx="26" cy="26" r="22" fill="none" stroke="#e4e4e7" strokeWidth="1.5" />
            <circle
              cx="26" cy="26" r="22"
              fill="none"
              stroke="#f59e0b"
              strokeWidth="2"
              strokeLinecap="round"
              strokeDasharray="46 92"
              style={{
                animation: "octane-spin 1.1s cubic-bezier(0.4, 0, 0.6, 1) infinite",
                transformOrigin: "26px 26px",
              }}
            />
          </svg>
        </div>

        {/* Wordmark */}
        <img
          src="/octane-logo-nav.svg"
          alt="Octane"
          style={{ width: 148, height: "auto", display: "block" }}
        />
      </div>

      {/* Byline */}
      <p
        className="absolute bottom-8 font-mono text-[10px] tracking-[0.06em] text-ink-600"
        style={{
          animation: "octane-enter 0.8s cubic-bezier(0.0, 0.0, 0.2, 1) 0.3s both",
          opacity: 0.4,
        }}
      >
        © 2026 Built by Ardeno
      </p>
    </div>
  );
}

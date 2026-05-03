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
      className="fixed inset-0 z-[9999] flex items-center justify-center"
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
      >
        <div className="relative flex items-center justify-center">
          {/* Ambient glow bloom */}
          <div
            className="absolute rounded-full"
            style={{
              width: 110,
              height: 110,
              background:
                "radial-gradient(circle, rgba(245,158,11,0.14) 0%, transparent 70%)",
              animation: "octane-bloom 2.2s ease-in-out infinite",
            }}
          />

          {/* SVG rings + arc */}
          <svg
            width="80"
            height="80"
            viewBox="0 0 80 80"
            style={{ position: "absolute" }}
          >
            {/* Subtle track ring */}
            <circle
              cx="40"
              cy="40"
              r="34"
              fill="none"
              stroke="#e4e4e7"
              strokeWidth="1.5"
            />
            {/* Spinning amber arc */}
            <circle
              cx="40"
              cy="40"
              r="34"
              fill="none"
              stroke="#f59e0b"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeDasharray="71 143"
              style={{
                animation:
                  "octane-spin 1.1s cubic-bezier(0.4, 0, 0.6, 1) infinite",
                transformOrigin: "40px 40px",
              }}
            />
          </svg>

          {/* Logo mark */}
          <img
            src="/octane-o.svg"
            alt="Octane"
            style={{
              width: 34,
              height: 34,
              position: "relative",
              zIndex: 1,
            }}
          />
        </div>
      </div>
    </div>
  );
}

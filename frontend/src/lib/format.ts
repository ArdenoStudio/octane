export function lkr(n: number, opts?: { showSymbol?: boolean }): string {
  const formatted = new Intl.NumberFormat("en-LK", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(n);
  return opts?.showSymbol === false ? formatted : `LKR ${formatted}`;
}

export function compactLkr(n: number): string {
  return `LKR ${new Intl.NumberFormat("en-LK", { maximumFractionDigits: 0 }).format(Math.round(n))}`;
}

export function shortDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}

export function relativeFromNow(iso: string): string {
  const d = new Date(iso);
  const diffMs = Date.now() - d.getTime();
  if (Number.isNaN(d.getTime())) return "";

  // Date-only revision stamps ("2026-04-01") stay day-granular.
  // Full timestamps (last_verified_at) use minute/hour precision.
  const hasTime = /T\d{2}:\d{2}/.test(iso);
  if (hasTime) {
    const minutes = Math.round(diffMs / (1000 * 60));
    if (minutes < 1) return "just now";
    if (minutes < 60) return `${minutes} min ago`;
    const hours = Math.round(minutes / 60);
    if (hours < 24) return hours === 1 ? "1 hour ago" : `${hours} hours ago`;
  }

  const days = Math.round(diffMs / (1000 * 60 * 60 * 24));
  if (days < 1) return "today";
  if (days === 1) return "yesterday";
  if (days < 30) return `${days} days ago`;
  const months = Math.round(days / 30);
  if (months < 12) return `${months} mo ago`;
  return `${Math.round(months / 12)} yr ago`;
}

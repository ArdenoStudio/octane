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
  const days = Math.round(diffMs / (1000 * 60 * 60 * 24));
  if (days < 1) return "today";
  if (days === 1) return "yesterday";
  if (days < 30) return `${days} days ago`;
  const months = Math.round(days / 30);
  if (months < 12) return `${months} mo ago`;
  return `${Math.round(months / 12)} yr ago`;
}

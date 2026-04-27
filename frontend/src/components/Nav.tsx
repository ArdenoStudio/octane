export function Nav() {
  return (
    <header className="sticky top-0 z-30 border-b border-ink-800/80 bg-ink-950/70 backdrop-blur">
      <div className="container-x flex h-14 items-center justify-between">
        <a href="/" className="flex items-center gap-2">
          <span
            aria-hidden
            className="grid h-8 w-8 place-items-center rounded-lg bg-accent text-ink-950 font-extrabold"
          >
            O
          </span>
          <span className="font-display text-lg font-bold tracking-tight">octane</span>
          <span className="ml-1 hidden text-xs uppercase tracking-[0.16em] text-ink-400 sm:inline">
            .lk
          </span>
        </a>
        <nav className="flex items-center gap-1 text-sm">
          <a href="#prices" className="px-3 py-1.5 text-ink-300 hover:text-ink-100">Prices</a>
          <a href="#calc" className="px-3 py-1.5 text-ink-300 hover:text-ink-100">Calculator</a>
          <a href="#history" className="px-3 py-1.5 text-ink-300 hover:text-ink-100">History</a>
          <a href="#alerts" className="px-3 py-1.5 text-ink-300 hover:text-ink-100">Alerts</a>
          <a href="#api" className="px-3 py-1.5 text-ink-300 hover:text-ink-100">API</a>
        </nav>
      </div>
    </header>
  );
}

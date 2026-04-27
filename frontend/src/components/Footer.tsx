export function Footer() {
  return (
    <footer className="container-x mt-20 border-t border-ink-800 py-10 text-sm text-ink-400">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          Built by{" "}
          <a
            href="https://ardenostudio.com"
            className="font-semibold text-ink-200 hover:text-accent"
          >
            Ardeno Studio
          </a>
          .
        </div>
        <div className="flex gap-4">
          <a href="#prices" className="hover:text-ink-200">Prices</a>
          <a href="#api" className="hover:text-ink-200">API</a>
          <a
            href="https://github.com"
            target="_blank"
            rel="noopener"
            className="hover:text-ink-200"
          >
            GitHub
          </a>
        </div>
      </div>
      <div className="mt-3 text-xs text-ink-400/70">
        Sources: Ceylon Petroleum Corporation, Lanka IOC, globalpetrolprices.com.
        Octane is independent and not affiliated with any of these organizations.
      </div>
    </footer>
  );
}

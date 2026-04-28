export function Footer() {
  const year = new Date().getFullYear()
  return (
    <div className="container-x mt-20">
      <footer className="relative pt-4">
        {/* Dashed vertical lines */}
        <div className="pointer-events-none absolute inset-0 select-none">
          <div
            className="absolute inset-y-0 w-px"
            style={{ maskImage: "linear-gradient(transparent, white 4rem)" }}
          >
            <svg className="h-full w-full" preserveAspectRatio="none">
              <line x1="0" y1="0" x2="0" y2="100%" className="stroke-ink-800" strokeWidth="1" strokeDasharray="3 3" />
            </svg>
          </div>
          <div
            className="absolute inset-y-0 right-0 w-px"
            style={{ maskImage: "linear-gradient(transparent, white 4rem)" }}
          >
            <svg className="h-full w-full" preserveAspectRatio="none">
              <line x1="0" y1="0" x2="0" y2="100%" className="stroke-ink-800" strokeWidth="1" strokeDasharray="3 3" />
            </svg>
          </div>
        </div>

        {/* Diagonal hatching strip */}
        <svg className="mb-8 h-16 w-full border-y border-dashed border-ink-800 stroke-ink-800/40">
          <defs>
            <pattern id="footer-diagonal" patternUnits="userSpaceOnUse" width="64" height="64">
              {Array.from({ length: 17 }, (_, i) => {
                const offset = i * 8
                return (
                  <path key={i} d={`M${-106 + offset} 110L${22 + offset} -18`} strokeWidth="1" />
                )
              })}
            </pattern>
          </defs>
          <rect stroke="none" width="100%" height="100%" fill="url(#footer-diagonal)" />
        </svg>

        <div className="flex flex-wrap items-center justify-between gap-3 pb-10 text-sm text-ink-400">
          <div>
            &copy; {year} Built by{" "}
            <a href="https://ardenostudio.com" className="font-semibold text-ink-200 hover:text-accent transition-colors">
              Ardeno Studio
            </a>
            .
          </div>
          <div className="flex gap-4">
            <a href="#prices" className="hover:text-ink-200 transition-colors">Prices</a>
            <a href="#api" className="hover:text-ink-200 transition-colors">API</a>
            <a href="https://github.com" target="_blank" rel="noopener" className="hover:text-ink-200 transition-colors">
              GitHub
            </a>
          </div>
        </div>

        <div className="pb-6 text-xs text-ink-600">
          Sources: Ceylon Petroleum Corporation, Lanka IOC, globalpetrolprices.com.
          Octane is independent and not affiliated with any of these organizations.
        </div>
      </footer>
    </div>
  )
}

import { useEffect } from "react";
import { RiCodeSSlashLine, RiDatabase2Line, RiExternalLinkLine, RiTimeLine } from "@remixicon/react";
import { ApiSection } from "../components/ApiSection";
import { EmbedSection } from "../components/EmbedSection";
import { Footer } from "../components/Footer";
import { Nav } from "../components/Nav";
import { api } from "../lib/api";

const STATS = [
  { icon: RiCodeSSlashLine, value: "8",      label: "Endpoints" },
  { icon: RiDatabase2Line,  value: "10yr+",  label: "Price history" },
  { icon: RiTimeLine,       value: "60/min", label: "Rate limit" },
];

export function DevelopersPage() {
  useEffect(() => {
    document.title = "Developers — Octane";
    return () => { document.title = "Octane — Live Sri Lanka Fuel Prices"; };
  }, []);

  return (
    <div className="min-h-screen">
      <Nav />
      <main>

        {/* ── Hero ── */}
        <section className="container-x pt-20 pb-4">
          <div className="max-w-2xl">
            <div className="label">Free public API</div>
            <h1 className="mt-2 font-display text-4xl font-extrabold tracking-tightest text-ink-100 sm:text-5xl">
              Build something with<br className="hidden sm:block" /> the data.
            </h1>
            <p className="mt-4 text-base leading-relaxed text-ink-400">
              Open endpoints — no API keys, no sign-up. Fuel prices, 10 years of history,
              world comparisons, and a trip cost calculator. Free for hobby projects,
              Slack bots, research, and more.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <a
                href={`${api.apiBase}/docs`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 rounded-xl bg-accent px-4 py-2 text-sm font-semibold text-white transition hover:bg-accent/90"
              >
                Interactive docs
                <RiExternalLinkLine className="size-3.5" />
              </a>
              <a
                href="#embed"
                className="inline-flex items-center gap-1.5 rounded-xl border border-ink-700 bg-ink-900 px-4 py-2 text-sm font-semibold text-ink-200 transition hover:border-ink-600 hover:text-ink-100"
              >
                Embed widget
              </a>
            </div>

            {/* Stats strip */}
            <div className="mt-10 flex flex-wrap gap-6">
              {STATS.map(({ icon: Icon, value, label }) => (
                <div key={label} className="flex items-center gap-2.5">
                  <div className="flex size-8 items-center justify-center rounded-lg border border-ink-800 bg-ink-900">
                    <Icon className="size-4 text-accent" />
                  </div>
                  <div>
                    <div className="text-sm font-bold text-ink-100">{value}</div>
                    <div className="text-xs text-ink-500">{label}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── Embed widget + API reference ── */}
        <div id="embed">
          <EmbedSection />
        </div>
        <ApiSection />

      </main>
      <Footer />
    </div>
  );
}

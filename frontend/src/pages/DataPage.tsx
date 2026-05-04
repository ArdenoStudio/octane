import { Nav } from "../components/Nav";
import { Footer } from "../components/Footer";
import { Badge } from "../components/ui/Badge";
import { FadeContainer, FadeDiv } from "../components/ui/Fade";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="border-t border-ink-800 pt-8">
      <h2 className="font-display text-xl font-extrabold tracking-tightest text-ink-100">
        {title}
      </h2>
      <div className="mt-3 space-y-3 text-sm leading-relaxed text-ink-300">
        {children}
      </div>
    </div>
  );
}

function Source({
  name,
  url,
  desc,
}: {
  name: string;
  url: string;
  desc: string;
}) {
  return (
    <div className="card p-4">
      <a
        href={url}
        target="_blank"
        rel="noopener noreferrer"
        className="font-semibold text-ink-200 hover:text-accent transition-colors"
      >
        {name} ↗
      </a>
      <p className="mt-1 text-xs text-ink-400">{desc}</p>
    </div>
  );
}

export function DataPage() {
  return (
    <div className="min-h-screen">
      <Nav />
      <main className="container-x py-10 sm:py-14">
        <FadeContainer>
          <FadeDiv>
            <Badge>Data methodology</Badge>
            <h1 className="mt-3 font-display text-3xl font-extrabold tracking-tightest text-ink-100 sm:text-4xl">
              How Octane collects and presents data.
            </h1>
            <p className="mt-3 text-ink-300">
              Octane is an independent data project by{" "}
              <a
                href="https://ardeno.studio"
                target="_blank"
                rel="noopener noreferrer"
                className="text-ink-200 hover:text-accent transition-colors underline-offset-2 hover:underline"
              >
                Ardeno Studio
              </a>
              . We are not affiliated with the Ceylon Petroleum Corporation,
              Lanka IOC, or any government body. This page documents our
              methodology so journalists, researchers, and developers can cite
              Octane with confidence.
            </p>
            <a
              href="/"
              className="mt-4 inline-block text-sm text-ink-400 hover:text-ink-200 transition-colors"
            >
              ← Back to live prices
            </a>
          </FadeDiv>

          <div className="mt-10 space-y-8">
            <Section title="Data sources">
              <p>
                Octane scrapes three primary sources. All prices are denominated
                in Sri Lankan Rupees (LKR) per litre.
              </p>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                <Source
                  name="Ceylon Petroleum Corporation (CPC)"
                  url="https://ceypetco.gov.lk"
                  desc="The primary source for all domestic retail prices. CPC is the state-owned entity responsible for setting and publishing fuel prices in Sri Lanka."
                />
                <Source
                  name="Lanka IOC"
                  url="https://www.lankaiocoil.lk"
                  desc="Indian Oil Corporation's Sri Lanka subsidiary. Prices typically follow CPC but may differ slightly. Used for cross-verification."
                />
                <Source
                  name="Global Petrol Prices"
                  url="https://www.globalpetrolprices.com"
                  desc="Used for world price comparison data. Provides weekly price snapshots across 170+ countries in USD per litre."
                />
              </div>
            </Section>

            <Section title="Collection methodology">
              <p>
                A scheduled scraper runs daily at{" "}
                <strong className="text-ink-200">08:00 Sri Lanka Time (UTC+5:30)</strong>
                . It fetches the current published prices from each source and
                stores them in a PostgreSQL database. Only revisions — records
                where the price differs from the prior entry for the same fuel
                and source — are stored as distinct events.
              </p>
              <p>
                Historical data going back to when records begin on each source
                website has been backfilled. The exact backfill date varies by
                fuel type and source.
              </p>
            </Section>

            <Section title="Currency conversion">
              <p>
                World comparison prices from Global Petrol Prices are published
                in USD. Octane converts these to LKR for comparison using the
                FX rate at the time of collection. FX rates are sourced from a
                public exchange rate API and stored alongside the price data.
                Historical LKR/USD comparisons reflect the FX rate at the time
                of collection, not today's rate.
              </p>
            </Section>

            <Section title="Data freshness">
              <p>
                Domestic CPC prices are refreshed daily. If the CPC website is
                unavailable or returns an unexpected format, the scraper logs an
                error and retains the last known price — no stale data is served
                without an explicit "last updated" timestamp.
              </p>
              <p>
                World prices from Global Petrol Prices are updated weekly
                (Monday). Regional comparisons may therefore lag domestic prices
                by up to 7 days.
              </p>
            </Section>

            <Section title="Citing Octane">
              <p>
                You are free to use Octane data in journalism, academic research,
                and policy analysis. When citing, please use:
              </p>
              <div className="rounded-xl border border-ink-800 bg-ink-900 px-4 py-3 font-mono text-xs text-ink-300">
                Octane — Live Sri Lanka Fuel Price Intelligence (octane.lk),
                Ardeno Studio. Data sourced from CPC (ceypetco.gov.lk) and
                Lanka IOC (lankaiocoil.lk). Retrieved [date].
              </div>
            </Section>

            <Section title="API access">
              <p>
                All data is available programmatically through the{" "}
                <a href="/#api" className="text-accent hover:underline">
                  free public API
                </a>
                . Historical data can be downloaded directly as CSV from the{" "}
                <a href="/#history" className="text-accent hover:underline">
                  price history chart
                </a>
                . No API key is required for basic access.
              </p>
              <p>
                For higher rate limits, bulk data exports, or commercial
                licensing, contact{" "}
                <a
                  href="mailto:hello@ardeno.studio"
                  className="text-accent hover:underline"
                >
                  hello@ardeno.studio
                </a>
                .
              </p>
            </Section>

            <Section title="Known limitations">
              <ul className="list-inside list-disc space-y-1 text-ink-400">
                <li>
                  CPC publishes prices on an ad-hoc basis. Between revisions,
                  the displayed price may be several weeks or months old.
                </li>
                <li>
                  Scraping accuracy depends on source website structure not
                  changing. Major redesigns may cause temporary data gaps.
                </li>
                <li>
                  World comparison data covers petrol and diesel categories only.
                  Kerosene world pricing is not available from our current
                  sources.
                </li>
              </ul>
            </Section>
          </div>
        </FadeContainer>
      </main>
      <Footer />
    </div>
  );
}

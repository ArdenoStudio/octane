import { useEffect } from "react";
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
  useEffect(() => {
    document.title = "Data Sources — Octane";
    return () => { document.title = "Octane — Live Sri Lanka Fuel Prices"; };
  }, []);

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
                href="https://ardeno-studio-website.vercel.app/"
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
                Octane scrapes several sources. Domestic retail prices are
                denominated in Sri Lankan Rupees (LKR) per litre.{" "}
                <strong className="text-ink-200">CPC and Lanka IOC</strong> are
                both treated as official — whichever published the more recent
                revision wins on the price cards.
              </p>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <Source
                  name="Ceylon Petroleum Corporation (CPC)"
                  url="https://ceypetco.gov.lk"
                  desc="State-owned retailer. One of two official sources for domestic pump prices."
                />
                <Source
                  name="Lanka IOC"
                  url="https://www.lankaioc.com"
                  desc="Indian Oil Corporation's Sri Lanka subsidiary. Also official — wins the card when its revision date is newer than CPC."
                />
                <Source
                  name="News outlets"
                  url="https://news.google.com"
                  desc="RSS feeds from Sri Lankan outlets. Early signal when media report a revision before official sites update. Shown as unconfirmed."
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
                A scheduled scraper checks CPC and Lanka IOC{" "}
                <strong className="text-ink-200">five times a day</strong>{" "}
                (approximately 08:00, 12:00, 16:00, 20:00, and midnight Sri Lanka
                Time). Each run fetches the currently published prices and
                upserts them into PostgreSQL, recording a verification timestamp
                even when neither source has published a new revision.
              </p>
              <p>
                Historical revision tables are backfilled from each source
                website. The exact backfill date varies by fuel type and source.
                Charts and change feeds highlight revision events — dates when
                the published price actually changed.
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
                Octane distinguishes <strong className="text-ink-200">last revision</strong>{" "}
                (when the winning official retail price changed) from{" "}
                <strong className="text-ink-200">last checked</strong> (when our
                scraper last successfully verified CPC or Lanka IOC). Official
                prices often sit unchanged for weeks; that does not mean Octane
                stopped updating. If a source website is unavailable or returns an
                unexpected format, the scraper logs an error and retains the last
                known price.
              </p>
              <p>
                When news outlets report a different figure ahead of the winning
                official source, Octane extends the history line with a{" "}
                <strong className="text-ink-200">dashed media segment</strong> and
                shows the figure on the price cards as unconfirmed — never as a
                second graph. When an official site publishes the real revision,
                that extension drops off. A daily market-context strip (AI outlook,
                USD/LKR, Sri Lanka vs world) updates even when retail prices are
                flat.
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
                Octane — Live Sri Lanka Fuel Price Intelligence (octane-smoky.vercel.app),
                Ardeno Studio. Data sourced from CPC (ceypetco.gov.lk) and
                Lanka IOC (lankaiocoil.lk). Retrieved [date].
              </div>
            </Section>

            <Section title="API access">
              <p>
                All data is available programmatically through the{" "}
                <a href="/developers" className="text-accent hover:underline">
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
                  href="mailto:ardenostudio@gmail.com"
                  className="text-accent hover:underline"
                >
                  ardenostudio@gmail.com
                </a>
                .
              </p>
            </Section>

            <Section title="Known limitations">
              <ul className="list-inside list-disc space-y-1 text-ink-400">
                <li>
                  CPC publishes prices on an ad-hoc basis. Between revisions the
                  retail price itself may be weeks old, even while Octane keeps
                  verifying the source several times a day.
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

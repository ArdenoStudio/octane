import { useEffect } from "react";
import { Nav } from "../components/Nav";
import { Footer } from "../components/Footer";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="border-t border-ink-800 pt-8">
      <h2 className="font-display text-xl font-extrabold tracking-tightest text-ink-100">{title}</h2>
      <div className="mt-3 space-y-3 text-sm leading-relaxed text-ink-300">{children}</div>
    </div>
  );
}

export function TermsPage() {
  useEffect(() => {
    document.title = "Terms of Use — Octane";
    return () => { document.title = "Octane — Live Sri Lanka Fuel Prices"; };
  }, []);

  return (
    <div className="min-h-screen">
      <Nav />
      <main className="container-x pb-24 pt-16">
        <div className="max-w-2xl">
          <div className="label">Legal</div>
          <h1 className="mt-2 font-display text-4xl font-extrabold tracking-tightest text-ink-100">
            Terms of Use
          </h1>
          <p className="mt-4 text-sm text-ink-500">Last updated: May 2025</p>

          <div className="mt-10 space-y-8">
            <Section title="About Octane">
              <p>
                Octane is a free, independent fuel price tracking service for Sri Lanka operated by{" "}
                <a href="https://ardeno-studio-website.vercel.app/" className="text-ink-100 underline underline-offset-2 hover:text-accent transition-colors">
                  Ardeno Studio
                </a>
                . By using this site or its API you agree to these terms.
              </p>
            </Section>

            <Section title="Data accuracy">
              <p>
                Fuel prices displayed on Octane are sourced from publicly available data published by the
                Ceylon Petroleum Corporation (CPC), Lanka IOC, and globalpetrolprices.com. We make
                reasonable efforts to keep this data current and accurate, but we make no guarantees.
              </p>
              <p>
                Prices may be delayed, incorrect, or out of date. <span className="text-ink-100">Do not
                rely on Octane as your sole source of truth</span> for fuel prices before making financial
                or logistical decisions. Always verify with the official CPC or Lanka IOC announcements.
              </p>
            </Section>

            <Section title="No affiliation">
              <p>
                Octane is an independent project and is not affiliated with, endorsed by, or in any way
                connected to the Ceylon Petroleum Corporation, Lanka IOC, the Government of Sri Lanka, or
                globalpetrolprices.com.
              </p>
            </Section>

            <Section title="No liability">
              <p>
                To the fullest extent permitted by law, Ardeno Studio shall not be liable for any loss,
                damage, or inconvenience arising from:
              </p>
              <ul className="list-disc pl-5 space-y-1.5">
                <li>Inaccurate, delayed, or missing price data.</li>
                <li>Reliance on price alerts that were not triggered, were delayed, or contained incorrect values.</li>
                <li>Downtime or interruption of the service.</li>
                <li>Any decision made based on information provided by Octane.</li>
              </ul>
              <p>The service is provided "as is", without warranty of any kind.</p>
            </Section>

            <Section title="Price alerts">
              <p>
                Price alerts are best-effort notifications. Delivery depends on third-party email
                infrastructure and is not guaranteed. Alert thresholds are checked when official price
                changes are published — not in real-time. We are not responsible for missed or delayed alerts.
              </p>
            </Section>

            <Section title="API usage">
              <p>
                The Octane public API is free for personal projects, research, and non-commercial use.
                Commercial use or high-volume usage requires prior written permission. We reserve the right
                to rate-limit or block any client that causes excessive load on the service.
              </p>
            </Section>

            <Section title="Service availability">
              <p>
                We provide no uptime guarantee. We may modify, suspend, or shut down the service at any
                time without notice.
              </p>
            </Section>

            <Section title="Changes to these terms">
              <p>
                We may update these terms from time to time. Continued use of the service after changes
                are posted constitutes acceptance of the revised terms.
              </p>
            </Section>

            <Section title="Contact">
              <p>
                Questions? Reach us at{" "}
                <a href="mailto:ardenostudio@gmail.com" className="text-ink-100 underline underline-offset-2 hover:text-accent transition-colors">
                  ardenostudio@gmail.com
                </a>
                .
              </p>
            </Section>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}

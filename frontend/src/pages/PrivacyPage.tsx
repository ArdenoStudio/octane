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

export function PrivacyPage() {
  useEffect(() => {
    document.title = "Privacy Policy — Octane";
    return () => { document.title = "Octane — Live Sri Lanka Fuel Prices"; };
  }, []);

  return (
    <div className="min-h-screen">
      <Nav />
      <main className="container-x pb-24 pt-16">
        <div className="max-w-2xl">
          <div className="label">Legal</div>
          <h1 className="mt-2 font-display text-4xl font-extrabold tracking-tightest text-ink-100">
            Privacy Policy
          </h1>
          <p className="mt-4 text-sm text-ink-500">Last updated: May 2025</p>

          <div className="mt-10 space-y-8">
            <Section title="Who we are">
              <p>
                Octane is an independent fuel price tracker for Sri Lanka, built and operated by{" "}
                <a href="https://ardeno-studio-website.vercel.app/" className="text-ink-100 underline underline-offset-2 hover:text-accent transition-colors">
                  Ardeno Studio
                </a>
                . We are not affiliated with the Ceylon Petroleum Corporation, Lanka IOC, or any government body.
              </p>
            </Section>

            <Section title="What we collect">
              <p>We collect only what is necessary to provide the service:</p>
              <ul className="list-disc pl-5 space-y-1.5">
                <li><span className="text-ink-100">Email address</span> — when you sign up for price alerts or the weekly digest.</li>
                <li><span className="text-ink-100">Alert preferences</span> — fuel type, price threshold, and direction (above/below).</li>
                <li><span className="text-ink-100">Anonymous usage data</span> — via Vercel Analytics (page views, referrers). No cookies are used. No personal information is collected by analytics.</li>
              </ul>
              <p>We do not collect names, payment information, or any other personal data.</p>
            </Section>

            <Section title="How we use your data">
              <ul className="list-disc pl-5 space-y-1.5">
                <li>To send you price alert emails when a fuel crosses your threshold.</li>
                <li>To send you the weekly fuel price digest (if subscribed).</li>
                <li>To improve the service based on anonymous usage patterns.</li>
              </ul>
              <p>We do not use your email for marketing, sell it to third parties, or share it for any purpose other than the above.</p>
            </Section>

            <Section title="Third-party services">
              <ul className="list-disc pl-5 space-y-1.5">
                <li><span className="text-ink-100">Vercel</span> — hosts the site and provides privacy-friendly, cookieless analytics.</li>
                <li><span className="text-ink-100">Email (SMTP)</span> — used to send alert and digest emails. Your address is not shared with the provider beyond what is needed to deliver the email.</li>
              </ul>
            </Section>

            <Section title="Data retention">
              <p>
                Your email and alert preferences are kept until you unsubscribe. You can unsubscribe at any
                time via the link in any email we send you. To request full deletion of your data, email us
                at{" "}
                <a href="mailto:ardenostudio@gmail.com" className="text-ink-100 underline underline-offset-2 hover:text-accent transition-colors">
                  ardenostudio@gmail.com
                </a>
                .
              </p>
            </Section>

            <Section title="Your rights">
              <p>You can at any time:</p>
              <ul className="list-disc pl-5 space-y-1.5">
                <li>Unsubscribe from alerts or the digest via the link in any email.</li>
                <li>Request a copy of the data we hold about you.</li>
                <li>Request deletion of your data.</li>
              </ul>
              <p>
                To exercise any of these rights, email{" "}
                <a href="mailto:ardenostudio@gmail.com" className="text-ink-100 underline underline-offset-2 hover:text-accent transition-colors">
                  ardenostudio@gmail.com
                </a>
                .
              </p>
            </Section>

            <Section title="Changes to this policy">
              <p>
                If we make material changes to this policy, we will update the date at the top of this page.
                Continued use of the service after changes constitutes acceptance of the revised policy.
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

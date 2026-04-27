import { api } from "../lib/api";

const SAMPLE = `curl ${"$"}{API}/v1/prices/latest`;

export function ApiSection() {
  return (
    <section id="api" className="container-x pt-16">
      <div className="card p-6 sm:p-8">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div>
            <div className="label">Free public API</div>
            <h2 className="mt-1 font-display text-3xl font-extrabold tracking-tightest sm:text-4xl">
              Build something with the data.
            </h2>
            <p className="mt-3 text-ink-300">
              Open endpoints. No keys for the basics. Rate-limited but generous —
              enough for a hobby project, a school assignment, or a Slack bot.
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <a
                href={`${api.apiBase}/docs`}
                target="_blank"
                rel="noopener"
                className="btn-primary"
              >
                Open API docs
              </a>
              <a href="#alerts" className="btn-ghost">Need higher limits?</a>
            </div>
          </div>
          <div>
            <div className="label">Try it</div>
            <pre className="mt-2 overflow-x-auto rounded-xl border border-ink-800 bg-ink-900 p-4 font-mono text-xs text-ink-200">
{`API="${api.apiBase}"

# Latest prices, all fuels
${SAMPLE}

# 2-year history, Petrol 92
curl "$API/v1/prices/history?fuel=petrol_92&days=730"

# Trip cost
curl "$API/v1/calculator/trip?distance=30&efficiency=12&fuel=petrol_92"`}
            </pre>
          </div>
        </div>
      </div>
    </section>
  );
}

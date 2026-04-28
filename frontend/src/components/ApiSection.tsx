import { api } from "../lib/api";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "./ui/Accordion";
import { Button } from "./ui/Button";
import { CopyToClipboard } from "./ui/CopyToClipboard";

const ENDPOINTS = [
  {
    id: "latest",
    label: "GET /v1/prices/latest",
    description: "Latest prices for all fuel types from CPC and Lanka IOC.",
    code: `curl "${api.apiBase}/v1/prices/latest"`,
  },
  {
    id: "history",
    label: "GET /v1/prices/history",
    description: "Up to 2 years of price history for a given fuel type.",
    code: `curl "${api.apiBase}/v1/prices/history?fuel=petrol_92&days=730"`,
  },
  {
    id: "calculator",
    label: "GET /v1/calculator/trip",
    description: "Calculate the fuel cost of a trip given distance and efficiency.",
    code: `curl "${api.apiBase}/v1/calculator/trip?distance=30&efficiency=12&fuel=petrol_92"`,
  },
]

export function ApiSection() {
  return (
    <section id="api" className="container-x pt-16">
      <div className="card p-6 sm:p-8">
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
          <div>
            <div className="label">Free public API</div>
            <h2 className="mt-1 font-display text-3xl font-extrabold tracking-tightest sm:text-4xl">
              Build something with the data.
            </h2>
            <p className="mt-3 text-ink-300">
              Open endpoints. No keys for the basics. Rate-limited but generous —
              enough for a hobby project, a school assignment, or a Slack bot.
            </p>
            <div className="mt-5 flex flex-wrap gap-2">
              <Button asChild>
                <a href={`${api.apiBase}/docs`} target="_blank" rel="noopener">
                  Open API docs
                </a>
              </Button>
              <Button variant="secondary" asChild>
                <a href="#alerts">Need higher limits?</a>
              </Button>
            </div>

            <div className="mt-8">
              <div className="label mb-3">Endpoints</div>
              <Accordion type="single" collapsible>
                {ENDPOINTS.map((ep) => (
                  <AccordionItem key={ep.id} value={ep.id}>
                    <AccordionTrigger>
                      <span className="font-mono text-xs text-ink-300">{ep.label}</span>
                    </AccordionTrigger>
                    <AccordionContent>
                      <p className="mb-3 text-ink-400">{ep.description}</p>
                      <div className="relative">
                        <pre className="overflow-x-auto rounded-xl border border-ink-800 bg-ink-900 p-3 font-mono text-xs text-ink-200">
                          {ep.code}
                        </pre>
                        <div className="absolute top-2 right-2">
                          <CopyToClipboard code={ep.code} />
                        </div>
                      </div>
                    </AccordionContent>
                  </AccordionItem>
                ))}
              </Accordion>
            </div>
          </div>

          <div>
            <div className="label">Quick start</div>
            <div className="relative mt-2">
              <pre className="overflow-x-auto rounded-xl border border-ink-800 bg-ink-900 p-4 font-mono text-xs text-ink-200">
{`API="${api.apiBase}"

# Latest prices, all fuels
curl "$API/v1/prices/latest"

# 2-year history, Petrol 92
curl "$API/v1/prices/history?fuel=petrol_92&days=730"

# Trip cost
curl "$API/v1/calculator/trip?distance=30&efficiency=12&fuel=petrol_92"`}
              </pre>
              <div className="absolute top-3 right-3">
                <CopyToClipboard code={`API="${api.apiBase}"

# Latest prices, all fuels
curl "$API/v1/prices/latest"

# 2-year history, Petrol 92
curl "$API/v1/prices/history?fuel=petrol_92&days=730"

# Trip cost
curl "$API/v1/calculator/trip?distance=30&efficiency=12&fuel=petrol_92"`} />
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

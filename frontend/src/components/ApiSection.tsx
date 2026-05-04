import { api } from "../lib/api";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "./ui/Accordion";
import { Button } from "./ui/Button";
import { CopyToClipboard } from "./ui/CopyToClipboard";

const ENDPOINTS = [
  {
    id: "latest",
    path: "/v1/prices/latest",
    description: "Latest prices for all fuel types from CPC and Lanka IOC.",
    code: `curl "${api.apiBase}/v1/prices/latest"`,
  },
  {
    id: "history",
    path: "/v1/prices/history",
    description: "Up to 2 years of price history for a given fuel type.",
    code: `curl "${api.apiBase}/v1/prices/history?fuel=petrol_92&days=730"`,
  },
  {
    id: "calculator",
    path: "/v1/calculator/trip",
    description: "Calculate the fuel cost of a trip given distance and efficiency.",
    code: `curl "${api.apiBase}/v1/calculator/trip?distance=30&efficiency=12&fuel=petrol_92"`,
  },
];

const quickStartCode = `API="${api.apiBase}"

# Latest prices, all fuels
curl "$API/v1/prices/latest"

# 2-year history, Petrol 92
curl "$API/v1/prices/history?fuel=petrol_92&days=730"

# Trip cost
curl "$API/v1/calculator/trip?distance=30&efficiency=12&fuel=petrol_92"`;

function SyntaxLine({ line }: { line: string }) {
  if (line === "") return <span>{"\n"}</span>;

  if (line.startsWith("#")) {
    return <span className="text-ink-600">{line}{"\n"}</span>;
  }

  const eqIdx = line.indexOf("=");
  if (eqIdx !== -1 && !line.startsWith("curl")) {
    return (
      <span>
        <span className="text-sky-600">{line.slice(0, eqIdx + 1)}</span>
        <span className="text-amber-600">{line.slice(eqIdx + 1)}</span>
        {"\n"}
      </span>
    );
  }

  if (line.startsWith("curl")) {
    const spaceIdx = line.indexOf(" ");
    return (
      <span>
        <span className="text-violet-500">{line.slice(0, spaceIdx)}</span>
        <span className="text-amber-600">{line.slice(spaceIdx)}</span>
        {"\n"}
      </span>
    );
  }

  return <span>{line}{"\n"}</span>;
}

function SyntaxHighlight({ code }: { code: string }) {
  return (
    <>
      {code.split("\n").map((line, i) => (
        <SyntaxLine key={i} line={line} />
      ))}
    </>
  );
}

export function ApiSection() {
  return (
    <section id="api" className="container-x pt-16">
      <div className="card overflow-hidden">
        <div className="grid grid-cols-1 lg:grid-cols-2">

          {/* Left — description + endpoints */}
          <div className="p-6 sm:p-8">
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
                      <span className="flex items-center gap-2">
                        <span className="rounded border border-emerald-200 bg-emerald-50 px-1.5 py-0.5 font-mono text-[10px] font-bold text-emerald-700">
                          GET
                        </span>
                        <span className="font-mono text-xs text-ink-300">{ep.path}</span>
                      </span>
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

          {/* Right — quick start code panel */}
          <div className="flex flex-col border-t border-ink-800 bg-ink-900 lg:border-t-0 lg:border-l">
            <div className="flex items-center gap-1.5 border-b border-ink-800 bg-ink-800 px-4 py-3">
              <span className="h-2.5 w-2.5 rounded-full bg-red-400/60" />
              <span className="h-2.5 w-2.5 rounded-full bg-yellow-400/60" />
              <span className="h-2.5 w-2.5 rounded-full bg-green-400/60" />
              <span className="ml-2 font-mono text-xs text-ink-500">quick-start.sh</span>
              <div className="ml-auto">
                <CopyToClipboard code={quickStartCode} />
              </div>
            </div>
            <div className="label px-4 pt-4 pb-1 sm:px-6">Quick start</div>
            <div className="flex-1 p-4 pt-2 sm:p-6 sm:pt-2">
              <pre className="overflow-x-auto font-mono text-xs leading-relaxed text-ink-200">
                <SyntaxHighlight code={quickStartCode} />
              </pre>
            </div>
          </div>

        </div>
      </div>
    </section>
  );
}

import { useState } from "react";
import { RiExternalLinkLine, RiLoader4Line, RiPlayCircleLine } from "@remixicon/react";
import { api } from "../lib/api";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "./ui/Accordion";
import { Button } from "./ui/Button";
import { CopyToClipboard } from "./ui/CopyToClipboard";

const BASE = api.apiBase;

interface Endpoint {
  id: string;
  method: "GET" | "POST";
  path: string;
  description: string;
  example: string;
  tryUrl?: string;
}

const ENDPOINTS: Endpoint[] = [
  {
    id: "latest",
    method: "GET",
    path: "/v1/prices/latest",
    description: "Latest prices for all fuel types from CPC and Lanka IOC.",
    example: `curl "${BASE}/v1/prices/latest"`,
    tryUrl: `${BASE}/v1/prices/latest`,
  },
  {
    id: "history",
    method: "GET",
    path: "/v1/prices/history",
    description: "Up to 10 years of daily price history for a given fuel type. Defaults to 730 days.",
    example: `curl "${BASE}/v1/prices/history?fuel=petrol_92&days=730"`,
    tryUrl: `${BASE}/v1/prices/history?fuel=petrol_92&days=30`,
  },
  {
    id: "changes",
    method: "GET",
    path: "/v1/prices/changes",
    description: "Price revision events with delta vs the previous price — the raw change log.",
    example: `curl "${BASE}/v1/prices/changes?limit=20"`,
    tryUrl: `${BASE}/v1/prices/changes?limit=10`,
  },
  {
    id: "csv",
    method: "GET",
    path: "/v1/prices/history.csv",
    description: "Download full price history as a CSV file. Supports multi-fuel and custom date ranges.",
    example: `curl -O "${BASE}/v1/prices/history.csv?fuel=petrol_92&fuel=auto_diesel&days=3650"`,
  },
  {
    id: "comparison",
    method: "GET",
    path: "/v1/comparison/world",
    description:
      "Sri Lanka vs world average and regional neighbours. Prices in USD using live FX rate.",
    example: `curl "${BASE}/v1/comparison/world?fuel=petrol_92"`,
    tryUrl: `${BASE}/v1/comparison/world?fuel=petrol_92`,
  },
  {
    id: "calculator",
    method: "GET",
    path: "/v1/calculator/trip",
    description: "Calculate fuel cost for a trip given distance (km) and efficiency (km/L).",
    example: `curl "${BASE}/v1/calculator/trip?distance=30&efficiency=12&fuel=petrol_92"`,
    tryUrl: `${BASE}/v1/calculator/trip?distance=30&efficiency=12&fuel=petrol_92`,
  },
  {
    id: "subscribe",
    method: "POST",
    path: "/v1/alerts/subscribe",
    description:
      "Subscribe to an email alert when a fuel crosses a threshold. Returns an unsubscribe token.",
    example: `curl -X POST "${BASE}/v1/alerts/subscribe" \\
  -H "Content-Type: application/json" \\
  -d '{"email":"you@example.com","fuel_type":"petrol_92","threshold":300,"direction":"below"}'`,
  },
  {
    id: "fuels",
    method: "GET",
    path: "/v1/fuels",
    description: "List all supported fuel type IDs and their display names.",
    example: `curl "${BASE}/v1/fuels"`,
    tryUrl: `${BASE}/v1/fuels`,
  },
];

const quickStartBash = `API="${BASE}"

# Latest prices, all fuels
curl "$API/v1/prices/latest"

# 1-year history, Petrol 92
curl "$API/v1/prices/history?fuel=petrol_92&days=365"

# Trip cost calculator
curl "$API/v1/calculator/trip?distance=30&efficiency=12&fuel=petrol_92"`;

const quickStartPython = `import httpx

API = "${BASE}"

# Latest prices
resp = httpx.get(f"{API}/v1/prices/latest")
for row in resp.json()["prices"]:
    print(row["fuel_type"], row["price_lkr"])

# Price history
history = httpx.get(f"{API}/v1/prices/history", params={
    "fuel": "petrol_92", "days": 365
}).json()["points"]`;

const quickStartJS = `const API = "${BASE}";

// Latest prices
const { prices } = await fetch(\`\${API}/v1/prices/latest\`).then(r => r.json());
console.log(prices);

// Trip cost
const trip = await fetch(
  \`\${API}/v1/calculator/trip?distance=30&efficiency=12&fuel=petrol_92\`
).then(r => r.json());
console.log(\`LKR \${trip.cost_lkr.toFixed(2)}\`);`;

const LANG_TABS = [
  { id: "bash", label: "bash", code: quickStartBash },
  { id: "python", label: "python", code: quickStartPython },
  { id: "js", label: "javascript", code: quickStartJS },
];

function SyntaxLine({ line }: { line: string }) {
  if (line === "") return <span>{"\n"}</span>;
  if (line.startsWith("#"))
    return <span className="text-ink-600">{line}{"\n"}</span>;

  const trimmed = line.trimStart();
  const indent = line.slice(0, line.length - trimmed.length);

  const eqIdx = line.indexOf("=");
  if (
    eqIdx !== -1 &&
    !trimmed.startsWith("curl") &&
    !trimmed.startsWith("import") &&
    !trimmed.startsWith(" ") &&
    indent === ""
  ) {
    return (
      <span>
        <span className="text-sky-500">{line.slice(0, eqIdx + 1)}</span>
        <span className="text-amber-500">{line.slice(eqIdx + 1)}</span>
        {"\n"}
      </span>
    );
  }
  if (trimmed.startsWith("curl")) {
    const spaceIdx = trimmed.indexOf(" ");
    return (
      <span>
        {indent}
        <span className="text-violet-400">{trimmed.slice(0, spaceIdx)}</span>
        <span className="text-amber-400">{trimmed.slice(spaceIdx)}</span>
        {"\n"}
      </span>
    );
  }
  if (trimmed.startsWith("import ") || trimmed.startsWith("const ") || trimmed.startsWith("await ")) {
    return <span className="text-sky-400">{line}{"\n"}</span>;
  }
  return <span className="text-ink-200">{line}{"\n"}</span>;
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

function MethodBadge({ method }: { method: "GET" | "POST" }) {
  return (
    <span
      className={`rounded border px-1.5 py-0.5 font-mono text-[10px] font-bold ${
        method === "GET"
          ? "border-emerald-200 bg-emerald-50 text-emerald-700"
          : "border-blue-200 bg-blue-50 text-blue-700"
      }`}
    >
      {method}
    </span>
  );
}

export function ApiSection() {
  const [activeLang, setActiveLang] = useState("bash");
  const [tryItUrl, setTryItUrl] = useState(`${BASE}/v1/prices/latest`);
  const [tryItResult, setTryItResult] = useState<string | null>(null);
  const [tryItLoading, setTryItLoading] = useState(false);
  const [tryItError, setTryItError] = useState<string | null>(null);

  const currentLang = LANG_TABS.find((t) => t.id === activeLang) ?? LANG_TABS[0];

  async function runTryIt() {
    setTryItLoading(true);
    setTryItResult(null);
    setTryItError(null);
    try {
      const r = await fetch(tryItUrl);
      const json = await r.json();
      const text = JSON.stringify(json, null, 2);
      // Truncate very large responses for readability
      setTryItResult(text.length > 3000 ? text.slice(0, 3000) + "\n  … (truncated)" : text);
    } catch (e) {
      setTryItError(String(e));
    } finally {
      setTryItLoading(false);
    }
  }

  return (
    <section id="api" className="container-x pt-16 pb-20">
      <div className="card overflow-hidden">
        <div className="grid grid-cols-1 lg:grid-cols-2">

          {/* ── Left: description + endpoint list ── */}
          <div className="p-6 sm:p-8">
            <div className="label">Free public API</div>
            <h2 className="mt-1 font-display text-3xl font-extrabold tracking-tightest sm:text-4xl">
              Build something with the data.
            </h2>
            <p className="mt-3 text-ink-300">
              Open endpoints, no keys required. Rate-limited at 60 req/min — enough for hobby
              projects, school assignments, or a Slack bot.
            </p>
            <div className="mt-5 flex flex-wrap gap-2">
              <Button asChild>
                <a
                  href={`${BASE}/docs`}
                  target="_blank"
                  rel="noopener"
                  className="inline-flex items-center gap-1.5"
                >
                  Interactive docs
                  <RiExternalLinkLine className="size-3.5" />
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
                        <MethodBadge method={ep.method} />
                        <span className="font-mono text-xs text-ink-300">{ep.path}</span>
                      </span>
                    </AccordionTrigger>
                    <AccordionContent>
                      <p className="mb-3 text-ink-400">{ep.description}</p>
                      <div className="relative">
                        <pre className="overflow-x-auto rounded-xl border border-ink-800 bg-ink-900 p-3 font-mono text-xs text-ink-200">
                          {ep.example}
                        </pre>
                        <div className="absolute top-2 right-2">
                          <CopyToClipboard code={ep.example} />
                        </div>
                      </div>
                      {ep.tryUrl && (
                        <button
                          onClick={() => {
                            setTryItUrl(ep.tryUrl!);
                            setTryItResult(null);
                            setTryItError(null);
                          }}
                          className="mt-2 flex items-center gap-1 text-xs text-accent hover:underline"
                        >
                          <RiPlayCircleLine className="size-3.5" />
                          Load in Try it
                        </button>
                      )}
                    </AccordionContent>
                  </AccordionItem>
                ))}
              </Accordion>
            </div>
          </div>

          {/* ── Right: code panel + try-it ── */}
          <div className="flex flex-col border-t border-ink-800 bg-ink-900 lg:border-t-0 lg:border-l">

            {/* Language tabs */}
            <div className="flex items-center gap-1.5 border-b border-ink-800 bg-ink-800 px-4 py-2">
              <span className="h-2.5 w-2.5 rounded-full bg-red-400/60" />
              <span className="h-2.5 w-2.5 rounded-full bg-yellow-400/60" />
              <span className="h-2.5 w-2.5 rounded-full bg-green-400/60" />
              <div className="ml-3 flex gap-1">
                {LANG_TABS.map((t) => (
                  <button
                    key={t.id}
                    onClick={() => setActiveLang(t.id)}
                    className={`rounded px-2 py-0.5 font-mono text-xs transition ${
                      activeLang === t.id
                        ? "bg-ink-700 text-ink-100"
                        : "text-ink-500 hover:text-ink-300"
                    }`}
                  >
                    {t.label}
                  </button>
                ))}
              </div>
              <div className="ml-auto">
                <CopyToClipboard code={currentLang!.code} />
              </div>
            </div>

            {/* Quick start code */}
            <div className="label px-4 pt-4 pb-1 sm:px-6">Quick start</div>
            <div className="p-4 pt-2 sm:p-6 sm:pt-2">
              <pre className="overflow-x-auto font-mono text-xs leading-relaxed text-ink-200">
                <SyntaxHighlight code={currentLang!.code} />
              </pre>
            </div>

            {/* Try it live */}
            <div className="border-t border-ink-800 p-4 sm:p-6">
              <div className="label mb-3">Try it live</div>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={tryItUrl}
                  onChange={(e) => setTryItUrl(e.target.value)}
                  spellCheck={false}
                  className="min-w-0 flex-1 rounded-lg border border-ink-700 bg-ink-800 px-3 py-1.5 font-mono text-xs text-ink-200 placeholder:text-ink-600 focus:border-accent focus:outline-none"
                />
                <button
                  onClick={runTryIt}
                  disabled={tryItLoading}
                  className="flex shrink-0 items-center gap-1.5 rounded-lg bg-accent px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-accent/90 disabled:opacity-60"
                >
                  {tryItLoading ? (
                    <RiLoader4Line className="size-3.5 animate-spin" />
                  ) : (
                    <RiPlayCircleLine className="size-3.5" />
                  )}
                  Run
                </button>
              </div>
              {tryItError && (
                <p className="mt-2 text-xs text-red-400">{tryItError}</p>
              )}
              {tryItResult && (
                <div className="relative mt-3">
                  <pre className="max-h-64 overflow-auto rounded-xl border border-ink-700 bg-ink-950 p-3 font-mono text-xs leading-relaxed text-emerald-300">
                    {tryItResult}
                  </pre>
                  <div className="absolute top-2 right-2">
                    <CopyToClipboard code={tryItResult} />
                  </div>
                </div>
              )}
            </div>

          </div>
        </div>
      </div>
    </section>
  );
}

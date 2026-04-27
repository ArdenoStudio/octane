import { useMemo, useState } from "react";
import { api, FUEL_DISPLAY, FUEL_ORDER, FuelId } from "../lib/api";

export function EmbedSection() {
  const [fuel, setFuel] = useState<FuelId>("petrol_92");
  const [theme, setTheme] = useState<"light" | "dark">("dark");
  const [copied, setCopied] = useState(false);

  const url = `${api.apiBase}/v1/embed/widget?fuel=${fuel}&theme=${theme}`;
  const snippet = useMemo(
    () =>
      `<iframe src="${url}" width="380" height="200" frameborder="0" style="border:0;border-radius:16px;"></iframe>`,
    [url]
  );

  async function copy() {
    try {
      await navigator.clipboard.writeText(snippet);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* no-op */
    }
  }

  return (
    <section className="container-x pt-16">
      <div className="card p-6 sm:p-8">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <div className="label">Embed widget</div>
            <h2 className="mt-1 font-display text-3xl font-extrabold tracking-tightest sm:text-4xl">
              Add live fuel prices to your site.
            </h2>
          </div>
          <div className="flex items-center gap-2">
            <select
              className="input w-auto"
              value={fuel}
              onChange={(e) => setFuel(e.target.value as FuelId)}
            >
              {FUEL_ORDER.map((f) => (
                <option key={f} value={f}>
                  {FUEL_DISPLAY[f]}
                </option>
              ))}
            </select>
            <select
              className="input w-auto"
              value={theme}
              onChange={(e) => setTheme(e.target.value as "light" | "dark")}
            >
              <option value="dark">dark</option>
              <option value="light">light</option>
            </select>
          </div>
        </div>

        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div className="rounded-xl border border-ink-800 bg-ink-950 p-3">
            <iframe
              key={url}
              src={url}
              title="Octane price widget preview"
              width="100%"
              height={200}
              className="block w-full rounded-lg"
              style={{ border: 0 }}
            />
          </div>
          <div>
            <pre className="overflow-x-auto rounded-xl border border-ink-800 bg-ink-900 p-4 font-mono text-xs text-ink-200">
              {snippet}
            </pre>
            <button onClick={copy} className="btn-ghost mt-3">
              {copied ? "Copied ✓" : "Copy snippet"}
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}

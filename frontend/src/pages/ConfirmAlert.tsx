import { useEffect, useState } from "react";
import { RiCheckLine } from "@remixicon/react";
import { api } from "../lib/api";
import { Nav } from "../components/Nav";
import { Footer } from "../components/Footer";

export function ConfirmAlert() {
  const token = new URLSearchParams(window.location.search).get("token") ?? "";

  useEffect(() => {
    document.title = "Confirm Alert — Octane";
    return () => { document.title = "Octane — Live Sri Lanka Fuel Prices"; };
  }, []);

  const [status, setStatus] = useState<"loading" | "ok" | "err">("loading");
  const [msg, setMsg] = useState("");

  useEffect(() => {
    if (!token) {
      setStatus("err");
      setMsg("No confirmation token found. Use the link from your signup email.");
      return;
    }
    api
      .confirmAlert(token)
      .then((r) => {
        setMsg(r.message);
        setStatus("ok");
      })
      .catch(() => {
        setStatus("err");
        setMsg("This confirmation link is invalid or has already been used.");
      });
  }, [token]);

  return (
    <div className="min-h-screen">
      <Nav />
      <main className="container-x py-16">
        <div className="mx-auto max-w-lg">
          <a
            href="/"
            className="mb-8 inline-flex items-center gap-1 text-sm text-ink-400 hover:text-ink-200 transition-colors"
          >
            ← Back to Octane
          </a>

          {status === "loading" && (
            <div className="card p-8 text-center text-ink-400">
              Confirming your alert…
            </div>
          )}

          {status === "ok" && (
            <div className="card p-8 text-center">
              <div className="mx-auto mb-4 flex size-12 items-center justify-center rounded-full bg-emerald-50">
                <RiCheckLine className="size-6 text-emerald-600" />
              </div>
              <h1 className="font-display text-2xl font-extrabold tracking-tightest text-ink-100">
                Alert confirmed
              </h1>
              <p className="mt-2 text-sm text-ink-300">{msg}</p>
              <a
                href="/"
                className="mt-6 inline-block text-sm text-accent hover:underline"
              >
                Back to Octane
              </a>
            </div>
          )}

          {status === "err" && (
            <div className="card p-8 text-center">
              <p className="text-ink-300">{msg}</p>
              <a
                href="/#alerts"
                className="mt-4 inline-block text-sm text-accent hover:underline"
              >
                Set a new alert
              </a>
            </div>
          )}
        </div>
      </main>
      <Footer />
    </div>
  );
}

import { useEffect } from "react";
import {
  RiArrowRightUpLine,
  RiBellLine,
  RiCarLine,
  RiCodeBoxLine,
  RiGasStationLine,
} from "@remixicon/react";
import { Footer } from "../components/Footer";
import { cx } from "../lib/utils";

const LINKS = ["Prices", "Calculator", "History", "Changes", "Data", "Developers"];

const DIRECTIONS = [
  {
    title: "A. Calm glass",
    intent: "Closest to the current product, but quieter: fewer heavy shadows, clearer rhythm, and a restrained alert button.",
    tags: ["safe", "ship-ready", "minimal"],
  },
  {
    title: "B. Command bar",
    intent: "More product-led and utility focused. Stronger active state, compact controls, and a clear system-bar feel.",
    tags: ["structured", "app-like", "sharp"],
  },
  {
    title: "C. Editorial strip",
    intent: "Feels more premium and content-led. The nav becomes a long soft strip with a status chip instead of a floating orb.",
    tags: ["premium", "calm", "wide"],
  },
  {
    title: "D. Split action",
    intent: "Keeps the memorable alert orb, but gives it better breathing room and makes the main navigation simpler.",
    tags: ["distinctive", "brandable", "desktop"],
  },
];

const FEATURE_LINKS = [
  { label: "Prices", Icon: RiGasStationLine },
  { label: "Alerts", Icon: RiBellLine },
  { label: "Trips", Icon: RiCarLine },
  { label: "API", Icon: RiCodeBoxLine },
];

function LogoWordmark({ inverse = false }: { inverse?: boolean }) {
  return (
    <div className={cx("font-serif text-[15px] font-semibold italic tracking-tight", inverse ? "text-white" : "text-zinc-950")}>
      Octane
    </div>
  );
}

function DotsBackground() {
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(24,24,27,0.18)_1px,transparent_1.2px)] [background-size:24px_24px] opacity-25" />
      <div className="absolute inset-x-0 top-0 h-40 bg-gradient-to-b from-amber-100/45 via-white/70 to-transparent" />
    </div>
  );
}

function LabFrame({
  title,
  intent,
  tags,
  children,
}: {
  title: string;
  intent: string;
  tags: string[];
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-[2rem] border border-zinc-200/80 bg-white p-4 shadow-sm sm:p-5">
      <div className="flex flex-col gap-3 border-b border-zinc-100 pb-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="font-display text-lg font-extrabold tracking-tight text-zinc-950">{title}</h2>
          <p className="mt-1 max-w-2xl text-sm leading-relaxed text-zinc-500">{intent}</p>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {tags.map((tag) => (
            <span key={tag} className="rounded-full border border-zinc-200 bg-zinc-50 px-2.5 py-1 text-[11px] font-semibold text-zinc-500">
              {tag}
            </span>
          ))}
        </div>
      </div>
      <div className="relative mt-5 min-h-40 overflow-hidden rounded-[1.5rem] border border-zinc-100 bg-white">
        <DotsBackground />
        {children}
      </div>
    </section>
  );
}

function LanguageSwitch({ dark = false }: { dark?: boolean }) {
  return (
    <div className={cx("flex rounded-full p-0.5", dark ? "bg-white/10 ring-1 ring-white/15" : "bg-zinc-100 ring-1 ring-black/5")}>
      {["EN", "සිං", "தமிழ்"].map((label, index) => (
        <span
          key={label}
          className={cx(
            "rounded-full px-2.5 py-1 text-[10px] font-bold",
            index === 0
              ? dark
                ? "bg-white text-zinc-950"
                : "bg-zinc-950 text-white"
              : dark
                ? "text-white/60"
                : "text-zinc-500",
          )}
        >
          {label}
        </span>
      ))}
    </div>
  );
}

function NavLinks({ active = "Prices", dark = false }: { active?: string; dark?: boolean }) {
  return (
    <div className="hidden items-center gap-0.5 md:flex">
      {LINKS.map((link) => (
        <span
          key={link}
          className={cx(
            "rounded-full px-3 py-2 text-[13px] font-semibold tracking-tight",
            link === active
              ? dark
                ? "bg-white text-zinc-950"
                : "bg-zinc-950 text-white"
              : dark
                ? "text-white/62"
                : "text-zinc-500",
          )}
        >
          {link}
        </span>
      ))}
    </div>
  );
}

function CalmGlassNav() {
  return (
    <div className="relative z-10 flex justify-center px-5 py-8">
      <div className="flex w-full max-w-5xl items-center gap-3 rounded-full border border-white/80 bg-white/78 px-4 py-2.5 shadow-[0_18px_55px_rgba(24,24,27,0.08),inset_0_1px_0_rgba(255,255,255,0.9)] backdrop-blur-xl">
        <LogoWordmark />
        <div className="mx-3 hidden h-5 w-px bg-zinc-200 sm:block" />
        <NavLinks active="Prices" />
        <div className="ml-auto flex items-center gap-2">
          <LanguageSwitch />
          <button className="hidden rounded-full bg-amber-400 px-4 py-2 text-xs font-extrabold text-zinc-950 shadow-[0_8px_18px_rgba(245,158,11,0.24)] sm:inline-flex">
            Get alerts
          </button>
        </div>
      </div>
    </div>
  );
}

function CommandBarNav() {
  return (
    <div className="relative z-10 flex justify-center px-5 py-8">
      <div className="flex w-full max-w-5xl items-center rounded-[1.35rem] bg-zinc-950 p-1.5 shadow-[0_22px_65px_rgba(24,24,27,0.22)]">
        <div className="flex h-11 items-center rounded-2xl bg-white px-4">
          <LogoWordmark />
        </div>
        <div className="mx-auto">
          <NavLinks active="Calculator" dark />
        </div>
        <div className="ml-auto flex items-center gap-1.5">
          <LanguageSwitch dark />
          <button className="inline-flex h-11 items-center gap-1.5 rounded-2xl bg-amber-400 px-4 text-xs font-extrabold text-zinc-950">
            Alerts
            <RiArrowRightUpLine className="size-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}

function EditorialStripNav() {
  return (
    <div className="relative z-10 px-5 py-8">
      <div className="mx-auto flex w-full max-w-5xl items-center gap-5 rounded-[1.75rem] border border-zinc-200/80 bg-white/86 px-5 py-3 shadow-[0_14px_45px_rgba(24,24,27,0.07)] backdrop-blur-xl">
        <LogoWordmark />
        <div className="hidden items-center gap-2 rounded-full bg-emerald-50 px-3 py-1.5 text-xs font-bold text-emerald-700 ring-1 ring-emerald-200/75 sm:flex">
          <span className="size-1.5 rounded-full bg-emerald-500" />
          CPC live
        </div>
        <NavLinks active="History" />
        <div className="ml-auto hidden items-center gap-4 lg:flex">
          <LanguageSwitch />
          <button className="text-sm font-extrabold text-zinc-950 underline decoration-amber-400 decoration-2 underline-offset-4">
            Set a price alert
          </button>
        </div>
      </div>
    </div>
  );
}

function SplitActionNav() {
  return (
    <div className="relative z-10 flex justify-center gap-3 px-5 py-8">
      <div className="flex w-full max-w-4xl items-center gap-3 rounded-full border border-zinc-200/70 bg-white/82 px-4 py-2.5 shadow-[0_18px_50px_rgba(24,24,27,0.075)] backdrop-blur-xl">
        <LogoWordmark />
        <div className="mx-auto">
          <NavLinks active="Data" />
        </div>
        <LanguageSwitch />
      </div>
      <button className="hidden size-16 shrink-0 flex-col items-center justify-center rounded-full border border-amber-700/25 bg-gradient-to-br from-amber-200 via-amber-400 to-orange-500 text-[10px] font-black leading-none text-zinc-950 shadow-[0_18px_40px_rgba(245,158,11,0.3),inset_0_1px_0_rgba(255,255,255,0.45)] sm:flex">
        <RiBellLine className="mb-1 size-4" />
        <span>Get</span>
        <span>Alerts</span>
      </button>
    </div>
  );
}

function FeatureMiniCards() {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {FEATURE_LINKS.map(({ label, Icon }) => (
        <div key={label} className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm">
          <div className="flex size-9 items-center justify-center rounded-xl bg-amber-50 text-amber-600 ring-1 ring-amber-100">
            <Icon className="size-4" />
          </div>
          <div className="mt-3 text-sm font-extrabold text-zinc-950">{label}</div>
          <p className="mt-1 text-xs leading-relaxed text-zinc-500">
            Supporting card style for this direction if the nav language expands into the hero.
          </p>
        </div>
      ))}
    </div>
  );
}

export function DesignLabPage() {
  useEffect(() => {
    document.title = "Design Lab - Octane";
    return () => {
      document.title = "Octane - Live Sri Lanka Fuel Prices";
    };
  }, []);

  return (
    <div className="min-h-screen bg-[#fbfaf8]">
      <main className="container-x py-10 sm:py-14">
        <a href="/" className="text-sm font-semibold text-zinc-500 transition hover:text-zinc-950">
          Back to Octane
        </a>
        <div className="mt-8 max-w-3xl">
          <div className="label">Navigation design lab</div>
          <h1 className="mt-3 font-display text-4xl font-extrabold tracking-tightest text-zinc-950 sm:text-6xl">
            Better directions before we ship another header.
          </h1>
          <p className="mt-4 text-base leading-relaxed text-zinc-500 sm:text-lg">
            The previous pass got too shiny. This lab keeps the same content and brand constraints, but separates the choices into clear visual directions.
          </p>
        </div>

        <div className="mt-10 space-y-6">
          <LabFrame {...DIRECTIONS[0]}>
            <CalmGlassNav />
          </LabFrame>
          <LabFrame {...DIRECTIONS[1]}>
            <CommandBarNav />
          </LabFrame>
          <LabFrame {...DIRECTIONS[2]}>
            <EditorialStripNav />
          </LabFrame>
          <LabFrame {...DIRECTIONS[3]}>
            <SplitActionNav />
          </LabFrame>
        </div>

        <section className="mt-8 rounded-[2rem] border border-zinc-200 bg-white p-5 shadow-sm">
          <h2 className="font-display text-lg font-extrabold tracking-tight text-zinc-950">
            Shared hero card language
          </h2>
          <p className="mt-1 max-w-2xl text-sm leading-relaxed text-zinc-500">
            If we pick one of the calmer directions, the supporting cards should also become cleaner and less folded/corner-heavy.
          </p>
          <div className="mt-5">
            <FeatureMiniCards />
          </div>
        </section>
      </main>
      <Footer />
    </div>
  );
}

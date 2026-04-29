import {
  RiArrowRightUpLine,
  RiBellLine,
  RiCarLine,
  RiCodeBoxLine,
  RiGasStationLine,
} from "@remixicon/react";
import { cx } from "../lib/utils";
import { FadeContainer, FadeDiv, FadeSpan } from "./ui/Fade";
import { HeroBackground } from "./HeroBackground";

interface FeatureCard {
  title: string;
  description: string;
  Icon: React.ElementType;
  href: string;
}

const FEATURES: FeatureCard[] = [
  {
    title: "Live prices",
    description: "CPC fuel prices updated daily, the moment revisions are published.",
    Icon: RiGasStationLine,
    href: "#prices",
  },
  {
    title: "Price alerts",
    description: "Set a threshold. Get emailed the instant any fuel crosses it.",
    Icon: RiBellLine,
    href: "#alerts",
  },
  {
    title: "Trip calculator",
    description: "Distance + efficiency = your exact fuel cost at today's prices.",
    Icon: RiCarLine,
    href: "#calc",
  },
  {
    title: "Free API",
    description: "Open REST endpoints. No key needed for basics. Build something.",
    Icon: RiCodeBoxLine,
    href: "#api",
  },
];

function Card({ title, description, Icon, href }: FeatureCard) {
  return (
    <a
      href={href}
      className={cx(
        // base layout
        "relative z-10 block overflow-hidden h-full",
        // shape — folded top-right corner
        "rounded-2xl rounded-tr-[26px] bg-white px-4 pt-5 pb-5",
        // inset border
        "shadow-[inset_0_0_0_1px_#e4e4e7]",
        // transition
        "transition-all duration-150 ease-in-out",
        // fold — diagonal square behind corner (before)
        "before:absolute before:top-0 before:right-0 before:z-[3]",
        "before:h-[30px] before:w-[30px]",
        "before:-translate-y-1/2 before:translate-x-1/2 before:rotate-45",
        "before:bg-ink-900 before:shadow-[0_1px_0_0_#d4d4d8]",
        "before:transition-all before:duration-150 before:ease-in-out before:content-['']",
        // fold cap — small square over corner (after)
        "after:absolute after:top-0 after:right-0 after:z-[2]",
        "after:h-7 after:w-7",
        "after:-translate-y-2 after:translate-x-2 after:rounded-bl-lg",
        "after:border after:bg-ink-900 after:transition-all after:duration-150 after:ease-in-out after:content-['']",
        // hover: corner grows
        "hover:rounded-tr-[45px]",
        "hover:before:h-[50px] hover:before:w-[50px]",
        "hover:after:h-[42px] hover:after:w-[42px] hover:after:shadow-lg hover:after:shadow-black/5",
        "hover:shadow-[inset_0_0_0_1px_#d4d4d8]",
      )}
    >
      <div className="relative flex items-center gap-2">
        <div className="absolute -left-4 h-5 w-[3px] rounded-r-sm bg-accent" />
        <Icon className="size-5 shrink-0 text-accent" />
        <h3 className="font-semibold text-ink-100">{title}</h3>
      </div>
      <p className="mt-2 text-sm text-ink-400">{description}</p>
    </a>
  );
}

export function HeroSection() {
  return (
    <section
      aria-label="hero"
      className="relative overflow-hidden"
    >
      {/* Game of Life background */}
      <div className="absolute inset-0 -z-10 flex items-start justify-center">
        <HeroBackground />
      </div>

      <FadeContainer className="container-x flex flex-col items-center justify-center pt-24 pb-16 text-center sm:pt-32 sm:pb-20">

        {/* Badge */}
        <FadeDiv delay={0} className="mx-auto">
          <a
            href="#prices"
            className="inline-flex max-w-full items-center gap-3 rounded-full bg-white/60 px-2.5 py-0.5 pr-3 pl-0.5 text-sm font-medium text-ink-200 ring-1 ring-ink-800 shadow-lg shadow-accent/10 backdrop-blur-[1px] transition-colors hover:bg-accent/5"
          >
            <span className="shrink-0 truncate rounded-full bg-red-500 px-2.5 py-1 text-xs text-black">
              Live
            </span>
            <span className="flex items-center gap-1 truncate">
              <span className="w-full truncate">
                CPC prices updated daily
              </span>
              <RiArrowRightUpLine className="size-4 shrink-0 text-ink-400" />
            </span>
          </a>
        </FadeDiv>

        {/* Headline */}
        <h1 className="mt-8 font-display text-5xl font-extrabold tracking-tightest text-ink-100 sm:text-7xl sm:leading-[1.05]">
          <FadeSpan delay={60}>Real</FadeSpan>{" "}
          <FadeSpan delay={110}>prices.</FadeSpan>
          <br />
          <FadeSpan delay={160}>Right</FadeSpan>{" "}
          <FadeSpan delay={210}>now.</FadeSpan>
        </h1>

        {/* Subheadline */}
        <p className="mt-5 max-w-xl text-base text-balance text-ink-400 sm:mt-7 sm:text-xl">
          <FadeSpan delay={270}>
            Sri Lanka fuel prices tracked daily from CPC —
          </FadeSpan>{" "}
          <FadeSpan delay={310}>
            with price history, alerts, a trip calculator,
          </FadeSpan>{" "}
          <FadeSpan delay={350}>and a free API.</FadeSpan>
        </p>

        {/* CTAs */}
        <FadeDiv delay={420} className="mt-8 flex flex-wrap items-center justify-center gap-3">
          <a
            href="#prices"
            className="inline-flex cursor-pointer items-center gap-1.5 rounded-md border-b-[1.5px] border-amber-600 bg-gradient-to-b from-amber-400 to-accent px-5 py-3 text-sm font-semibold leading-4 tracking-wide text-zinc-900 shadow-[0_0_0_2px_rgba(0,0,0,0.04),0_0_14px_0_rgba(255,255,255,0.19)] transition-all duration-200 ease-in-out hover:shadow-amber-300 whitespace-nowrap"
          >
            Check today's prices
          </a>
          <a
            href="#alerts"
            className="inline-flex items-center gap-1 rounded-md border border-ink-700 px-5 py-3 text-sm font-semibold text-ink-300 transition-all duration-150 hover:bg-ink-900 hover:text-ink-200 whitespace-nowrap"
          >
            Set a price alert
            <RiArrowRightUpLine className="size-4 text-ink-400" />
          </a>
        </FadeDiv>

        {/* Feature cards */}
        <FadeDiv delay={500} className="mt-14 w-full">
          <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
            {FEATURES.map((f) => (
              <Card key={f.title} {...f} />
            ))}
          </div>
        </FadeDiv>

      </FadeContainer>
    </section>
  );
}

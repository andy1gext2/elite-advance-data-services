"use client";

import Link from "next/link";
import { Button } from "@/components/ui";
import { LandingNav } from "@/components/landing/LandingNav";
import { Reveal } from "@/components/landing/Reveal";
import { CountUp } from "@/components/landing/CountUp";
import {
  CalendarMockup,
  ContentMockup,
  DashboardMockup,
  ReputationMockup,
} from "@/components/landing/Mockups";

const CHANNELS = [
  "Instagram", "Facebook", "LinkedIn", "X", "Threads",
  "Google Business", "Blog", "Email", "SMS", "YouTube", "TikTok",
];

const FEATURES = [
  {
    id: "content",
    eyebrow: "AI Social Media Manager",
    title: "One idea becomes a dozen perfect posts.",
    body: "Describe a thought in a sentence. Get platform-tailored content for every channel — optimized, on-brand, and ready to approve. Not copy-paste. Genuinely rewritten for how each audience reads.",
    Mockup: ContentMockup,
  },
  {
    id: "calendar",
    eyebrow: "AI Content Calendar",
    title: "A month of marketing, planned in seconds.",
    body: "Give a theme and a horizon. Your AI strategist proposes what to post, on which platform, and exactly when — then turns any slot into a scheduled post with a single click.",
    Mockup: CalendarMockup,
    flip: true,
  },
  {
    id: "reputation",
    eyebrow: "Reputation Manager",
    title: "Every review, handled with care.",
    body: "Monitor reviews across platforms, read the sentiment at a glance, and reply in your brand's voice with AI-drafted responses. Negative reviews get flagged before they cost you.",
    Mockup: ReputationMockup,
  },
];

const STATS = [
  { to: 10000, suffix: "+", label: "businesses at scale" },
  { to: 7, label: "tools replaced by one" },
  { to: 12, label: "posts from a single idea" },
  { to: 60, suffix: "s", label: "to plan a month" },
];

const PRICING = [
  { name: "Starter", price: "$29", tagline: "For solo owners getting started.",
    features: ["1 business", "150 AI generations / mo", "3 connected channels", "Content + calendar"] },
  { name: "Professional", price: "$79", tagline: "For growing brands.", featured: true,
    features: ["3 businesses", "1,000 AI generations / mo", "All channels", "Scheduling + reputation"] },
  { name: "Growth", price: "$199", tagline: "For teams and multi-location.",
    features: ["10 businesses", "5,000 AI generations / mo", "Team roles + approvals", "Analytics + insights"] },
  { name: "Enterprise", price: "Custom", tagline: "For agencies at scale.",
    features: ["Unlimited businesses", "Custom AI quota", "SSO + audit logs", "Dedicated support"] },
];

export default function LandingPage() {
  return (
    <div className="relative overflow-x-hidden">
      <LandingNav />

      {/* ── Hero ── */}
      <section className="relative flex min-h-screen items-center justify-center px-6 pt-16 text-center">
        {/* ambient background */}
        <div className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
          <div className="drift absolute -top-32 left-1/2 h-[38rem] w-[38rem] -translate-x-1/2 rounded-full bg-brand/15 blur-3xl" />
          <div className="drift absolute right-[-10rem] top-40 h-[26rem] w-[26rem] rounded-full bg-brand/10 blur-3xl [animation-delay:-6s]" />
        </div>

        <div className="mx-auto max-w-4xl">
          <Reveal>
            <span className="inline-flex items-center gap-2 rounded-full border border-border bg-surface/60 px-4 py-1.5 text-xs font-medium text-muted backdrop-blur">
              <span className="h-1.5 w-1.5 rounded-full bg-brand" />
              AI Marketing, Social & Reputation — in one platform
            </span>
          </Reveal>
          <Reveal delay={80}>
            <h1 className="display mt-7 text-6xl sm:text-7xl md:text-[5.5rem]">
              Your entire marketing team,{" "}
              <span className="shimmer-text">powered by AI</span>.
            </h1>
          </Reveal>
          <Reveal delay={160}>
            <p className="mx-auto mt-7 max-w-2xl text-balance text-xl leading-relaxed text-muted sm:text-2xl">
              Elite Advance creates your content, plans your calendar, publishes
              everywhere, and manages your reputation — so you can run your
              business instead of your marketing.
            </p>
          </Reveal>
          <Reveal delay={240}>
            <div className="mt-10 flex flex-col items-center justify-center gap-x-8 gap-y-4 sm:flex-row">
              <Link
                href="/signup"
                className="rounded-full bg-brand px-8 py-3.5 text-base font-medium text-brand-fg shadow-lg shadow-brand/20 transition-transform hover:scale-[1.03]"
              >
                Start free
              </Link>
              <a
                href="#features"
                className="text-base font-medium text-brand transition-transform hover:translate-x-0.5"
              >
                See how it works&nbsp;›
              </a>
            </div>
          </Reveal>

          <Reveal delay={320}>
            <div className="floaty mx-auto mt-16 max-w-2xl">
              <DashboardMockup />
            </div>
          </Reveal>
        </div>
      </section>

      {/* ── Channel marquee ── */}
      <section className="border-y border-border py-10">
        <p className="mb-6 text-center text-xs font-medium uppercase tracking-[0.2em] text-muted">
          Publishes and listens across every channel
        </p>
        <div className="relative overflow-hidden [mask-image:linear-gradient(to_right,transparent,black_12%,black_88%,transparent)]">
          <div className="marquee flex w-max gap-10 whitespace-nowrap pr-10 text-xl font-semibold text-fg/40">
            {[...CHANNELS, ...CHANNELS].map((c, i) => (
              <span key={i} className="flex items-center gap-10">
                {c}
                <span className="text-brand/40">•</span>
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* ── Feature showcases ── */}
      <section id="features" className="mx-auto max-w-6xl px-6 py-24 sm:py-32">
        <Reveal className="mx-auto max-w-2xl text-center">
          <p className="text-sm font-semibold uppercase tracking-widest text-brand">
            The platform
          </p>
          <h2 className="display mt-3 text-4xl sm:text-5xl">
            Everything a marketing department does. Automated.
          </h2>
        </Reveal>

        <div className="mt-20 space-y-28">
          {FEATURES.map(({ id, eyebrow, title, body, Mockup, flip }) => (
            <div
              key={id}
              className="grid items-center gap-10 md:grid-cols-2 md:gap-16"
            >
              <Reveal className={flip ? "md:order-2" : ""}>
                <p className="text-sm font-semibold uppercase tracking-widest text-brand">
                  {eyebrow}
                </p>
                <h3 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">
                  {title}
                </h3>
                <p className="mt-5 text-lg leading-relaxed text-muted">{body}</p>
                <Link
                  href="/signup"
                  className="mt-6 inline-flex items-center gap-1.5 text-sm font-semibold text-brand transition-transform hover:translate-x-0.5"
                >
                  Try it free →
                </Link>
              </Reveal>
              <Reveal delay={120} className={flip ? "md:order-1" : ""}>
                <Mockup />
              </Reveal>
            </div>
          ))}
        </div>
      </section>

      {/* ── Big statement + stats ── */}
      <section
        id="platform"
        className="relative overflow-hidden bg-brand px-6 py-24 text-brand-fg sm:py-32"
      >
        <div className="mx-auto max-w-4xl text-center">
          <Reveal>
            <h2 className="display text-4xl sm:text-6xl">
              Built to replace your entire stack.
            </h2>
            <p className="mx-auto mt-6 max-w-2xl text-balance text-lg leading-relaxed text-brand-fg/70">
              Provider-agnostic AI, isolated per-platform connectors, and a
              real-time dashboard — engineered for thousands of businesses and
              millions of posts.
            </p>
          </Reveal>
          <div className="mt-16 grid grid-cols-2 gap-8 sm:grid-cols-4">
            {STATS.map((s, i) => (
              <Reveal key={s.label} delay={i * 90}>
                <p className="text-4xl font-bold tracking-tight sm:text-5xl">
                  <CountUp to={s.to} suffix={s.suffix} />
                </p>
                <p className="mt-2 text-sm text-brand-fg/70">{s.label}</p>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* ── Pricing ── */}
      <section id="pricing" className="mx-auto max-w-6xl px-6 py-24 sm:py-32">
        <Reveal className="mx-auto max-w-2xl text-center">
          <p className="text-sm font-semibold uppercase tracking-widest text-brand">
            Pricing
          </p>
          <h2 className="display mt-3 text-4xl sm:text-5xl">
            Simple plans that scale with you.
          </h2>
        </Reveal>

        <div className="mt-16 grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          {PRICING.map((p, i) => (
            <Reveal key={p.name} delay={i * 80}>
              <div
                className={
                  "flex h-full flex-col rounded-2xl border p-6 transition-transform duration-300 hover:-translate-y-1 " +
                  (p.featured
                    ? "border-brand bg-brand/5 shadow-xl shadow-brand/10"
                    : "border-border bg-surface")
                }
              >
                {p.featured && (
                  <span className="mb-3 inline-block w-fit rounded-full bg-brand px-3 py-1 text-xs font-semibold text-brand-fg">
                    Most popular
                  </span>
                )}
                <h3 className="text-lg font-semibold">{p.name}</h3>
                <p className="mt-1 text-sm text-muted">{p.tagline}</p>
                <p className="mt-4 text-3xl font-bold tracking-tight">
                  {p.price}
                  {p.price !== "Custom" && (
                    <span className="text-sm font-normal text-muted">/mo</span>
                  )}
                </p>
                <ul className="mt-5 space-y-2 text-sm">
                  {p.features.map((f) => (
                    <li key={f} className="flex gap-2">
                      <span className="text-brand">✓</span>
                      <span className="text-fg/80">{f}</span>
                    </li>
                  ))}
                </ul>
                <Link href="/signup" className="mt-6 block">
                  <Button
                    variant={p.featured ? "primary" : "secondary"}
                    className="w-full rounded-full"
                  >
                    {p.price === "Custom" ? "Contact sales" : "Start free"}
                  </Button>
                </Link>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* ── Closing CTA ── */}
      <section className="px-6 py-24 sm:py-32">
        <Reveal className="mx-auto max-w-3xl rounded-[2rem] border border-border bg-surface px-8 py-20 text-center shadow-2xl shadow-brand/5">
          <h2 className="display text-4xl sm:text-5xl">
            Hire your AI marketing team today.
          </h2>
          <p className="mx-auto mt-5 max-w-xl text-lg leading-relaxed text-muted">
            Set up your business in minutes. Generate your first campaign before
            your coffee gets cold.
          </p>
          <div className="mt-9 flex justify-center">
            <Link
              href="/signup"
              className="rounded-full bg-brand px-8 py-3.5 text-base font-medium text-brand-fg shadow-lg shadow-brand/20 transition-transform hover:scale-[1.03]"
            >
              Start free
            </Link>
          </div>
        </Reveal>
      </section>

      {/* ── Footer ── */}
      <footer className="border-t border-border px-6 py-12">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 text-sm text-muted sm:flex-row">
          <span>© 2026 Elite Advance Data Services</span>
          <div className="flex gap-6">
            <a href="#features" className="hover:text-fg">Features</a>
            <a href="#pricing" className="hover:text-fg">Pricing</a>
            <Link href="/login" className="hover:text-fg">Sign in</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { CHANNEL_COLORS, CHANNEL_LABELS, type IndustryTrend } from "@/lib/types";
import { Card } from "@/components/ui";

// Dashboard card: AI-inferred, seasonally-aware trends for the business's
// industry. Collapsible to save space — when collapsed it shows a right-to-left
// marquee "peek" of the trending hashtags; expanded it shows the full brief
// (keywords / products / services / seasonal) plus concrete post ideas. Each idea
// deep-links into the Content studio with its brief prefilled (via sessionStorage).

const COLLAPSE_KEY = "trendsCollapsed";

// "patio dining" → "#PatioDining"; keeps an existing leading '#'.
function toHashtag(s: string): string {
  const t = s.trim().replace(/^#+/, "");
  const camel = t
    .split(/\s+/)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join("");
  const clean = camel.replace(/[^A-Za-z0-9]/g, "");
  return clean ? `#${clean}` : "";
}

function ChipRow({
  label,
  items,
  accent,
}: {
  label: string;
  items: string[];
  accent?: boolean;
}) {
  if (!items.length) return null;
  return (
    <div>
      <p className="mb-1.5 text-[11px] font-medium uppercase tracking-wide text-muted">
        {label}
      </p>
      <div className="flex flex-wrap gap-1.5">
        {items.map((t, i) => (
          <span
            key={i}
            className={
              "rounded-full px-2.5 py-1 text-xs " +
              (accent
                ? "border border-brand/40 bg-brand/10 text-brand"
                : "border border-border bg-bg text-fg/80")
            }
          >
            {t}
          </span>
        ))}
      </div>
    </div>
  );
}

// Right-to-left seamless marquee of the trending hashtags (the collapsed "peek").
function HashtagMarquee({ tags }: { tags: string[] }) {
  if (!tags.length) return null;
  return (
    <div className="group overflow-hidden py-0.5" title="Trending hashtags">
      {/* Content is duplicated so the -50% translate loops seamlessly. */}
      <div className="marquee flex w-max gap-2 whitespace-nowrap group-hover:[animation-play-state:paused]">
        {[...tags, ...tags].map((t, i) => (
          <span
            key={i}
            className="rounded-full border border-brand/30 bg-brand/10 px-2.5 py-1 text-xs font-medium text-brand"
          >
            {t}
          </span>
        ))}
      </div>
    </div>
  );
}

export function TrendsCard({ businessId }: { businessId: string }) {
  const router = useRouter();
  const [trend, setTrend] = useState<IndustryTrend | null>(null);
  const [error, setError] = useState("");
  const [locked, setLocked] = useState(false); // 402 → plan doesn't include trends
  const [loading, setLoading] = useState(true);
  const [collapsed, setCollapsed] = useState(true); // default compact; peek marquee

  // Restore the saved open/closed preference (client-only, avoids hydration mismatch).
  useEffect(() => {
    const saved = localStorage.getItem(COLLAPSE_KEY);
    if (saved != null) setCollapsed(saved === "1");
  }, []);

  function toggle() {
    setCollapsed((c) => {
      const next = !c;
      localStorage.setItem(COLLAPSE_KEY, next ? "1" : "0");
      return next;
    });
  }

  useEffect(() => {
    let alive = true;
    api
      .businessTrends(businessId)
      .then((t) => alive && setTrend(t))
      .catch((e) => {
        if (!alive) return;
        if (e instanceof ApiError && e.status === 402) setLocked(true);
        else setError(e instanceof ApiError ? e.message : "Could not load trends");
      })
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [businessId]);

  function draft(idea: { title: string; channel: string }) {
    sessionStorage.setItem(
      "draftBrief",
      JSON.stringify({ brief: idea.title, channel: idea.channel })
    );
    router.push(`/businesses/${businessId}/content`);
  }

  const hashtags = trend
    ? Array.from(
        new Set([...trend.seasonal, ...trend.keywords].map(toHashtag).filter(Boolean))
      )
    : [];

  return (
    <Card>
      {/* Header — click anywhere (or the chevron) to expand/collapse. */}
      <button
        type="button"
        onClick={toggle}
        aria-expanded={!collapsed}
        className="flex w-full items-center justify-between gap-2 text-left"
      >
        <span className="flex items-center gap-2">
          <span
            className={
              "text-muted transition-transform " + (collapsed ? "" : "rotate-90")
            }
            aria-hidden
          >
            ▸
          </span>
          <span className="text-sm font-semibold">
            🔥 Trending{trend ? ` in ${trend.display_industry}` : ""}
          </span>
        </span>
        <span className="flex items-center gap-2">
          <span className="rounded-full border border-amber-500/40 bg-amber-500/10 px-2 py-0.5 text-[11px] font-medium text-amber-600 dark:text-amber-400">
            AI · seasonal
          </span>
          <span className="text-[11px] text-muted">{collapsed ? "Expand" : "Collapse"}</span>
        </span>
      </button>

      {/* Collapsed: a slim right-to-left marquee peek of the trending hashtags. */}
      {collapsed ? (
        <div className="mt-2">
          {loading ? (
            <p className="text-xs text-muted">Reading the latest trends…</p>
          ) : locked ? (
            <p className="text-xs text-muted">
              🔒 Industry trends —{" "}
              <Link
                href={`/businesses/${businessId}/billing`}
                className="text-brand hover:underline"
                onClick={(e) => e.stopPropagation()}
              >
                upgrade to unlock
              </Link>
            </p>
          ) : hashtags.length ? (
            <HashtagMarquee tags={hashtags} />
          ) : error ? (
            <p className="text-xs text-muted">{error}</p>
          ) : null}
        </div>
      ) : (
        /* Expanded: the full brief. */
        <div className="mt-3">
          {loading ? (
            <p className="text-sm text-muted">Reading the latest trends…</p>
          ) : locked ? (
            <div className="rounded-lg border border-dashed border-border bg-bg p-4">
              <p className="text-sm text-fg/90">
                🔒 <span className="font-medium">Industry trend suggestions</span> are a
                Professional feature.
              </p>
              <p className="mt-1 text-xs text-muted">
                Upgrade to get seasonal, industry-tailored ideas for what to post next —
                keywords, hot products &amp; services, and ready-to-draft post ideas.
              </p>
              <Link
                href={`/businesses/${businessId}/billing`}
                className="mt-3 inline-block rounded-lg border border-brand/50 px-3 py-1.5 text-xs font-medium text-brand hover:bg-brand/10"
              >
                View plans →
              </Link>
            </div>
          ) : error ? (
            <p className="text-sm text-muted">
              {error.includes("industry")
                ? "Set your business industry (⋯ → Edit) to unlock trend suggestions."
                : error}
            </p>
          ) : trend ? (
            <div className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <ChipRow label="Seasonal right now" items={trend.seasonal} accent />
                <ChipRow label="Trending keywords" items={trend.keywords} />
                <ChipRow label="Hot products" items={trend.products} />
                <ChipRow label="In-demand services" items={trend.services} />
              </div>

              {trend.post_ideas.length > 0 && (
                <div>
                  <p className="mb-2 text-[11px] font-medium uppercase tracking-wide text-muted">
                    Post ideas for you
                  </p>
                  <ul className="space-y-2">
                    {trend.post_ideas.map((idea, i) => (
                      <li
                        key={i}
                        className="flex items-start justify-between gap-3 rounded-lg border border-border bg-bg p-3"
                      >
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <span
                              className="inline-block h-2 w-2 shrink-0 rounded-full"
                              style={{
                                backgroundColor:
                                  CHANNEL_COLORS[idea.channel] ?? CHANNEL_COLORS.generic,
                              }}
                              aria-hidden
                            />
                            <p className="truncate text-sm font-medium">{idea.title}</p>
                          </div>
                          {idea.why && (
                            <p className="mt-0.5 text-xs text-muted">{idea.why}</p>
                          )}
                          <p className="mt-0.5 text-[11px] text-muted">
                            Suggested for {CHANNEL_LABELS[idea.channel] ?? idea.channel}
                          </p>
                        </div>
                        <button
                          onClick={() => draft(idea)}
                          className="shrink-0 rounded-lg border border-brand/50 px-2.5 py-1.5 text-xs font-medium text-brand hover:bg-brand/10"
                        >
                          ✍ Draft this
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <p className="text-[11px] text-muted">
                AI-inferred seasonal guidance for {trend.display_industry.toLowerCase()} —
                refreshed monthly.
              </p>
            </div>
          ) : null}
        </div>
      )}
    </Card>
  );
}

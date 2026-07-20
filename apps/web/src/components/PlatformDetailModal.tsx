"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  CHANNEL_COLORS,
  CHANNEL_LABELS,
  type PlatformAnalytics,
} from "@/lib/types";
import { LineChart } from "@/components/charts";

// Per-platform drill-down opened by clicking a slice of the "Content by channel"
// wheel. Shows that single platform's engagement tiles + a Platform-performance
// trend chart scoped to just that platform. Data comes from the same
// PlatformAnalytics payload the dashboard already loaded (per_platform + series),
// so no extra request is needed.

type Metric = "reach" | "engagement" | "clicks" | "mentions";
const METRIC_LABELS: Record<Metric, string> = {
  reach: "Reach",
  engagement: "Engagement",
  clicks: "Clicks",
  mentions: "Mentions",
};

const n = (v: number | undefined) => (v ?? 0).toLocaleString("en-US");

function Tile({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-lg border border-border bg-bg p-3">
      <p className="text-[11px] font-medium uppercase tracking-wide text-muted">{label}</p>
      <p className="mt-1 text-xl font-semibold tabular-nums">{value}</p>
      {hint && <p className="text-[11px] text-muted">{hint}</p>}
    </div>
  );
}

export function PlatformDetailModal({
  businessId,
  channel,
  postCount,
  analytics,
  onClose,
}: {
  businessId: string;
  channel: string;
  postCount: number;
  analytics: PlatformAnalytics | null;
  onClose: () => void;
}) {
  const [metric, setMetric] = useState<Metric>("reach");

  // Close on Escape.
  const close = useCallback(() => onClose(), [onClose]);
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") close();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [close]);

  const label = CHANNEL_LABELS[channel] ?? channel;
  const color = CHANNEL_COLORS[channel] ?? CHANNEL_COLORS.generic;

  // Look up this platform's tiles + trend from the analytics payload.
  const stats = analytics?.per_platform.find((p) => p.platform === channel) ?? null;
  const trend = analytics?.series.platforms.find((p) => p.platform === channel) ?? null;
  const isLocal = stats?.kind === "local";

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 p-4 backdrop-blur-sm sm:p-8"
      onMouseDown={close}
    >
      <div
        className="my-auto w-full max-w-4xl rounded-2xl border border-border bg-surface shadow-xl"
        onMouseDown={(e) => e.stopPropagation()}
      >
        {/* Header — branded to the platform color. */}
        <div className="flex items-center justify-between gap-3 border-b border-border px-5 py-4">
          <div className="flex items-center gap-3">
            <span
              className="inline-block h-3.5 w-3.5 rounded-full"
              style={{ backgroundColor: color }}
              aria-hidden
            />
            <div>
              <h2 className="text-base font-semibold">{label} analytics</h2>
              <p className="text-xs text-muted">
                {postCount} {postCount === 1 ? "post" : "posts"} on this channel
              </p>
            </div>
          </div>
          <button
            onClick={close}
            aria-label="Close"
            className="rounded-md px-2 text-xl leading-none text-muted hover:text-fg"
          >
            ×
          </button>
        </div>

        <div className="space-y-6 p-5">
          {analytics?.simulated && (
            <span className="inline-block rounded-full border border-amber-500/40 bg-amber-500/10 px-2 py-0.5 text-[11px] font-medium text-amber-600 dark:text-amber-400">
              Sample data
            </span>
          )}

          {!stats && !trend ? (
            <div className="rounded-lg border border-dashed border-border bg-bg p-6 text-center">
              <p className="text-sm text-muted">
                No engagement analytics for {label} yet.
              </p>
              <p className="mt-1 text-xs text-muted">
                Reach, engagement, and clicks appear once a {label} account is{" "}
                <Link
                  href={`/businesses/${businessId}/schedule`}
                  className="text-brand hover:underline"
                >
                  connected on the Schedule tab
                </Link>
                . Channels like Blog, Email, and SMS don&apos;t report platform metrics.
              </p>
            </div>
          ) : (
            <>
              {/* KPI tiles — social vs. Google Business (local). */}
              {stats && (
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                  {isLocal ? (
                    <>
                      <Tile label="Views" value={n(stats.views)} hint="Search + Maps" />
                      <Tile label="Actions" value={n(stats.actions)} />
                    </>
                  ) : (
                    <>
                      <Tile label="Reach" value={n(stats.reach)} />
                      <Tile label="Impressions" value={n(stats.impressions)} />
                      <Tile
                        label="Engagement"
                        value={`${stats.engagement_rate ?? 0}%`}
                        hint={`${n(stats.engagements)} interactions`}
                      />
                      <Tile
                        label="Clicks"
                        value={n(stats.link_clicks)}
                        hint={`${stats.ctr ?? 0}% CTR`}
                      />
                      <Tile label="Followers" value={n(stats.followers)} />
                      <Tile
                        label="Follower growth"
                        value={`${(stats.follower_growth ?? 0) >= 0 ? "+" : ""}${n(stats.follower_growth)}`}
                        hint="last 28 days"
                      />
                    </>
                  )}
                </div>
              )}

              {/* Platform performance — trend scoped to just this platform. */}
              {trend && (
                <div>
                  <div className="mb-3 flex items-center justify-between gap-2">
                    <p className="text-xs font-medium uppercase tracking-wide text-muted">
                      {label} · {METRIC_LABELS[metric]} · last 8 weeks
                    </p>
                    <select
                      value={metric}
                      onChange={(e) => setMetric(e.target.value as Metric)}
                      className="rounded-lg border border-border bg-bg px-2.5 py-1.5 text-sm text-fg outline-none focus:border-brand"
                    >
                      {(Object.keys(METRIC_LABELS) as Metric[]).map((m) => (
                        <option key={m} value={m}>
                          {METRIC_LABELS[m]}
                        </option>
                      ))}
                    </select>
                  </div>
                  <LineChart
                    labels={analytics?.series.weeks ?? []}
                    series={[{ label, color, values: trend[metric] }]}
                  />
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

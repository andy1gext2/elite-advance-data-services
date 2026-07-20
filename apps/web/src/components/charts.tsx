"use client";

import { useState } from "react";

// Lightweight, dependency-free charts built from the design-system tokens.
// Each chart is a single measure → single brand hue, so no legend is needed
// (the heading names the series). Marks are thin, rounded at the data end, sit on
// the baseline, and separate with a 2px surface gap. Per-mark hover uses native
// title tooltips. Sentiment is the one diverging case: two hues + a gray midpoint.

function fmtWeek(iso: string) {
  const [y, m, d] = iso.split("-").map(Number);
  return `${m}/${d}`;
}

export function WeeklyBars({ data }: { data: { week: string; count: number }[] }) {
  const max = Math.max(1, ...data.map((d) => d.count));
  return (
    <div>
      <div className="flex h-24 items-end gap-0.5">
        {data.map((d) => (
          <div
            key={d.week}
            className="flex h-full flex-1 items-end"
            title={`Week of ${fmtWeek(d.week)}: ${d.count}`}
          >
            <div
              className="w-full rounded-t bg-brand"
              style={{
                height: `${(d.count / max) * 100}%`,
                minHeight: d.count > 0 ? 4 : 0,
              }}
            />
          </div>
        ))}
      </div>
      <div className="mt-1 flex justify-between border-t border-border pt-1 text-[10px] text-muted">
        <span>{fmtWeek(data[0]?.week ?? "")}</span>
        <span>peak {max}</span>
        <span>{fmtWeek(data[data.length - 1]?.week ?? "")}</span>
      </div>
    </div>
  );
}

export function HBars({ data }: { data: { label: string; value: number }[] }) {
  if (data.length === 0)
    return <p className="text-sm text-muted">No data yet.</p>;
  const max = Math.max(1, ...data.map((d) => d.value));
  return (
    <div className="space-y-2">
      {data.map((d) => (
        <div key={d.label} className="flex items-center gap-2 text-sm">
          <span className="w-24 shrink-0 truncate capitalize text-muted">
            {d.label}
          </span>
          <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-border/50">
            <div
              className="h-full rounded-full bg-brand"
              style={{ width: `${(d.value / max) * 100}%` }}
              title={`${d.label}: ${d.value}`}
            />
          </div>
          <span className="w-6 text-right tabular-nums">{d.value}</span>
        </div>
      ))}
    </div>
  );
}

// Part-to-whole share of a single measure across categories. One brand hue,
// stepped by share (largest = solid, smaller = faded) — magnitude, not a rainbow.
// The legend carries each label + count + %, so identity is never color-alone.
export function Donut({
  data,
  size = 128,
}: {
  data: { label: string; value: number; color?: string }[];
  size?: number;
}) {
  const items = data.filter((d) => d.value > 0).sort((a, b) => b.value - a.value);
  const total = items.reduce((sum, d) => sum + d.value, 0);
  const [hover, setHover] = useState<number | null>(null);
  if (total === 0) return <p className="text-sm text-muted">No data yet.</p>;

  const r = 42;
  const C = 2 * Math.PI * r;
  const gap = items.length > 1 ? 1.5 : 0; // px of surface ring between slices
  let offset = 0;
  const arcs = items.map((d, i) => {
    const frac = d.value / total;
    const len = Math.max(frac * C - gap, 0);
    const base = d.color ? 1 : Math.max(1 - i * 0.16, 0.4);
    const arc = { len, dash: `${len} ${C - len}`, offset: -offset, base, color: d.color };
    offset += frac * C;
    return arc;
  });

  const active = hover != null ? items[hover] : null;
  const activePct = active ? Math.round((active.value / total) * 100) : 0;

  return (
    <div className="flex flex-col items-center">
      <svg
        viewBox="0 0 100 100"
        style={{ height: size, width: size }}
        className="-rotate-90"
      >
        <circle cx="50" cy="50" r={r} fill="none" className="stroke-border" strokeWidth="14" />
        {arcs.map((a, i) => {
          // Hover: raise the active slice (thicker) and dim the rest.
          const opacity = hover == null ? a.base : hover === i ? 1 : 0.15;
          const width = hover === i ? 20 : 14;
          return (
            <circle
              key={i}
              cx="50"
              cy="50"
              r={r}
              fill="none"
              className={a.color ? undefined : "stroke-brand"}
              stroke={a.color}
              strokeWidth={width}
              strokeDasharray={a.dash}
              strokeDashoffset={a.offset}
              strokeOpacity={opacity}
              onMouseEnter={() => setHover(i)}
              onMouseLeave={() => setHover(null)}
              style={{ transition: "stroke-width 150ms, stroke-opacity 150ms", cursor: "pointer" }}
            />
          );
        })}
        {/* Center: total by default; the hovered channel's count + share on hover. */}
        <text x="50" y="46" transform="rotate(90 50 50)" textAnchor="middle" dominantBaseline="central" className="fill-fg text-[16px] font-semibold">
          {active ? active.value : total}
        </text>
        <text x="50" y="61" transform="rotate(90 50 50)" textAnchor="middle" dominantBaseline="central" className="fill-muted text-[7px]">
          {active ? `${activePct}%` : "posts"}
        </text>
      </svg>
      {/* Legend labels which color is which channel. Counts + % stay on hover
          (shown in the wheel's center). Hovering a label also raises its slice. */}
      <div className="mt-3 flex flex-wrap justify-center gap-x-3 gap-y-1">
        {items.map((d, i) => (
          <button
            key={d.label}
            type="button"
            onMouseEnter={() => setHover(i)}
            onMouseLeave={() => setHover(null)}
            className={
              "flex items-center gap-1.5 text-xs transition-colors " +
              (hover === i ? "font-medium text-fg" : "text-muted")
            }
          >
            <span
              className={"h-2 w-2 shrink-0 rounded-sm " + (d.color ? "" : "bg-brand")}
              style={
                d.color
                  ? { background: d.color }
                  : { opacity: Math.max(1 - i * 0.16, 0.4) }
              }
            />
            <span className="capitalize">{d.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

// Multi-line trend chart. One line per series, each its own color. Dependency-
// free SVG; strokes stay uniform width via non-scaling-stroke while the viewBox
// stretches to fill. Legend + axis labels carry identity (never color-alone).
export function LineChart({
  labels,
  series,
  height = 150,
}: {
  labels: string[];
  series: { label: string; color: string; values: number[] }[];
  height?: number;
}) {
  const max = Math.max(1, ...series.flatMap((s) => s.values));
  const n = labels.length;
  const W = 100;
  const H = 100;
  const x = (i: number) => (n <= 1 ? 0 : (i / (n - 1)) * W);
  const y = (v: number) => H - (v / max) * H;

  if (series.length === 0)
    return <p className="text-sm text-muted">No trend data yet.</p>;

  return (
    <div>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="none"
        style={{ height }}
        className="w-full overflow-visible"
      >
        {/* baseline + mid gridline */}
        <line x1="0" y1={H} x2={W} y2={H} className="stroke-border" strokeWidth="1" vectorEffect="non-scaling-stroke" />
        <line x1="0" y1={H / 2} x2={W} y2={H / 2} className="stroke-border" strokeWidth="1" strokeDasharray="2 3" vectorEffect="non-scaling-stroke" opacity={0.5} />
        {series.map((s) => (
          <polyline
            key={s.label}
            fill="none"
            stroke={s.color}
            strokeWidth="2"
            strokeLinejoin="round"
            strokeLinecap="round"
            vectorEffect="non-scaling-stroke"
            points={s.values.map((v, i) => `${x(i)},${y(v)}`).join(" ")}
          />
        ))}
      </svg>
      <div className="mt-1 flex justify-between border-t border-border pt-1 text-[10px] text-muted">
        <span>{labels[0]}</span>
        <span>peak {max.toLocaleString("en-US")}</span>
        <span>{labels[n - 1]}</span>
      </div>
      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1">
        {series.map((s) => (
          <span key={s.label} className="flex items-center gap-1.5 text-xs text-muted">
            <span className="h-2.5 w-2.5 rounded-sm" style={{ background: s.color }} />
            {s.label}
          </span>
        ))}
      </div>
    </div>
  );
}

export function SentimentBar({ s }: { s: Record<string, number> }) {
  const pos = s.positive || 0;
  const neu = s.neutral || 0;
  const neg = s.negative || 0;
  const total = pos + neu + neg || 1;
  return (
    <div>
      <div className="flex h-3 overflow-hidden rounded-full">
        <div
          className="bg-green-600 dark:bg-green-500"
          style={{ width: `${(pos / total) * 100}%` }}
          title={`Positive: ${pos}`}
        />
        <div
          className="bg-zinc-400"
          style={{ width: `${(neu / total) * 100}%` }}
          title={`Neutral: ${neu}`}
        />
        <div
          className="bg-red-500"
          style={{ width: `${(neg / total) * 100}%` }}
          title={`Negative: ${neg}`}
        />
      </div>
      <div className="mt-2 flex flex-wrap gap-4 text-xs text-muted">
        <span>😊 {pos} positive</span>
        <span>😐 {neu} neutral</span>
        <span>☹️ {neg} negative</span>
      </div>
    </div>
  );
}

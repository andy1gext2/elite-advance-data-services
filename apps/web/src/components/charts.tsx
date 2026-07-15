"use client";

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
export function Donut({ data }: { data: { label: string; value: number }[] }) {
  const items = data.filter((d) => d.value > 0).sort((a, b) => b.value - a.value);
  const total = items.reduce((sum, d) => sum + d.value, 0);
  if (total === 0) return <p className="text-sm text-muted">No data yet.</p>;

  const r = 42;
  const C = 2 * Math.PI * r;
  const gap = items.length > 1 ? 1.5 : 0; // px of surface ring between slices
  let offset = 0;
  const arcs = items.map((d, i) => {
    const frac = d.value / total;
    const len = Math.max(frac * C - gap, 0);
    // Largest slice fully opaque; each smaller step fades toward the ground.
    const opacity = Math.max(1 - i * 0.16, 0.4);
    const arc = { len, dash: `${len} ${C - len}`, offset: -offset, opacity };
    offset += frac * C;
    return arc;
  });

  return (
    <div className="flex items-center gap-5">
      <svg viewBox="0 0 100 100" className="h-32 w-32 -rotate-90 shrink-0">
        <circle cx="50" cy="50" r={r} fill="none" className="stroke-border" strokeWidth="15" />
        {arcs.map((a, i) => (
          <circle
            key={i}
            cx="50"
            cy="50"
            r={r}
            fill="none"
            className="stroke-brand"
            strokeWidth="15"
            strokeDasharray={a.dash}
            strokeDashoffset={a.offset}
            strokeOpacity={a.opacity}
          />
        ))}
        <text
          x="50"
          y="50"
          transform="rotate(90 50 50)"
          textAnchor="middle"
          dominantBaseline="central"
          className="fill-fg text-[15px] font-semibold"
        >
          {total}
        </text>
      </svg>
      <ul className="min-w-0 flex-1 space-y-1.5">
        {items.map((d, i) => (
          <li key={d.label} className="flex items-center gap-2 text-sm">
            <span
              className="h-2.5 w-2.5 shrink-0 rounded-sm bg-brand"
              style={{ opacity: Math.max(1 - i * 0.16, 0.4) }}
            />
            <span className="min-w-0 flex-1 truncate capitalize text-muted">{d.label}</span>
            <span className="tabular-nums">{d.value}</span>
            <span className="w-9 text-right text-xs tabular-nums text-muted">
              {Math.round((d.value / total) * 100)}%
            </span>
          </li>
        ))}
      </ul>
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

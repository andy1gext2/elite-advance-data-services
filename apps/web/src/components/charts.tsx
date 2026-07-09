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

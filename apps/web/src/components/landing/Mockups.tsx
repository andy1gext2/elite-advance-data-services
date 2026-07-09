// Stylized product "screenshots" for the landing page — built with the real design
// tokens so the marketing visuals match the actual app. Purely presentational.

function Frame({ children }: { children: React.ReactNode }) {
  return (
    <div className="overflow-hidden rounded-2xl border border-border bg-surface shadow-2xl shadow-brand/5">
      <div className="flex items-center gap-1.5 border-b border-border bg-bg/60 px-4 py-3">
        <span className="h-2.5 w-2.5 rounded-full bg-border" />
        <span className="h-2.5 w-2.5 rounded-full bg-border" />
        <span className="h-2.5 w-2.5 rounded-full bg-border" />
      </div>
      <div className="p-5">{children}</div>
    </div>
  );
}

function Bars({ heights }: { heights: number[] }) {
  const max = Math.max(...heights);
  return (
    <div className="flex h-24 items-end gap-1.5">
      {heights.map((h, i) => (
        <div
          key={i}
          className="flex-1 rounded-t bg-brand"
          style={{ height: `${(h / max) * 100}%` }}
        />
      ))}
    </div>
  );
}

export function DashboardMockup() {
  return (
    <Frame>
      <div className="grid grid-cols-3 gap-3">
        {[
          ["Content", "128"],
          ["Avg rating", "4.6★"],
          ["Published", "342"],
        ].map(([label, value]) => (
          <div key={label} className="rounded-xl border border-border p-3">
            <p className="text-[10px] uppercase tracking-wide text-muted">
              {label}
            </p>
            <p className="mt-1 text-lg font-semibold">{value}</p>
          </div>
        ))}
      </div>
      <div className="mt-4 rounded-xl border border-border p-4">
        <p className="mb-3 text-xs font-medium text-muted">Content / week</p>
        <Bars heights={[3, 5, 4, 7, 6, 9, 8, 12]} />
      </div>
      <div className="mt-3 flex gap-3">
        <div className="flex-1 rounded-xl border border-border p-3">
          <p className="mb-2 text-xs font-medium text-muted">Sentiment</p>
          <div className="flex h-2.5 overflow-hidden rounded-full">
            <div className="bg-green-600 dark:bg-green-500" style={{ width: "62%" }} />
            <div className="bg-zinc-400" style={{ width: "22%" }} />
            <div className="bg-red-500" style={{ width: "16%" }} />
          </div>
        </div>
      </div>
    </Frame>
  );
}

export function ContentMockup() {
  const chips = ["Instagram", "LinkedIn", "X", "Facebook", "Threads", "Blog"];
  return (
    <Frame>
      <div className="rounded-xl border border-border p-4">
        <p className="text-xs font-medium text-muted">Your idea</p>
        <p className="mt-1 text-sm">
          Launching a fall pumpkin spice cold brew — limited time.
        </p>
      </div>
      <div className="my-3 flex items-center gap-2 text-xs text-brand">
        <span className="h-px flex-1 bg-border" />
        ✨ Repurposed into 12 posts
        <span className="h-px flex-1 bg-border" />
      </div>
      <div className="flex flex-wrap gap-2">
        {chips.map((c) => (
          <span
            key={c}
            className="rounded-full border border-brand/30 bg-brand/10 px-3 py-1 text-xs font-medium text-brand"
          >
            {c}
          </span>
        ))}
      </div>
      <div className="mt-4 space-y-2">
        {["Cozy season is here ☕ Meet our new…", "This fall, we're pouring something…"].map(
          (t) => (
            <div
              key={t}
              className="flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-xs"
            >
              <span className="rounded-full bg-green-500/15 px-2 py-0.5 text-[10px] font-medium text-green-600 dark:text-green-500">
                approved
              </span>
              <span className="truncate text-fg/80">{t}</span>
            </div>
          )
        )}
      </div>
    </Frame>
  );
}

export function CalendarMockup() {
  const slots = [
    ["MON", "9", "LinkedIn", "Thought-leadership on seasonal trends"],
    ["WED", "11", "Instagram", "Behind-the-scenes of the new blend"],
    ["FRI", "8", "X", "Limited-time launch announcement"],
  ];
  return (
    <Frame>
      <div className="space-y-3">
        {slots.map(([d, n, ch, topic]) => (
          <div key={n} className="flex items-start gap-3 rounded-xl border border-border p-3">
            <div className="flex w-11 flex-col items-center rounded-lg border border-border bg-bg py-1 text-center">
              <span className="text-[10px] font-medium uppercase text-muted">{d}</span>
              <span className="text-lg font-semibold leading-none">{n}</span>
            </div>
            <div className="min-w-0 flex-1">
              <span className="rounded-full border border-brand/30 bg-brand/10 px-2 py-0.5 text-[10px] font-medium text-brand">
                {ch}
              </span>
              <p className="mt-1.5 truncate text-xs text-fg/80">{topic}</p>
            </div>
          </div>
        ))}
      </div>
    </Frame>
  );
}

export function ReputationMockup() {
  return (
    <Frame>
      <div className="rounded-xl border border-border p-4">
        <div className="flex items-center gap-2">
          <span className="text-amber-500">★★★★★</span>
          <span className="text-xs font-medium">Jordan P.</span>
          <span className="ml-auto rounded-full bg-green-500/15 px-2 py-0.5 text-[10px] font-medium text-green-600 dark:text-green-500">
            positive
          </span>
        </div>
        <p className="mt-2 text-xs text-fg/80">
          Absolutely love this place — the staff are so friendly and the coffee
          is amazing!
        </p>
        <div className="mt-3 rounded-lg border border-border bg-bg p-3">
          <p className="mb-1 text-[10px] font-medium text-brand">✨ AI reply</p>
          <p className="text-xs text-fg/80">
            Thank you so much, Jordan! The whole team appreciates it — see you
            again soon ☕
          </p>
        </div>
      </div>
    </Frame>
  );
}

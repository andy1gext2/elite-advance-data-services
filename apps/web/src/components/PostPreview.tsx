"use client";

// Renders a generated post as it would appear on each platform — authentic chrome
// plus a generated visual. The visual is a stylized on-brand placeholder (a real
// image/video model drops in later, like the text provider); it reuses any emoji
// the copy already contains so it feels designed, not random.

// ── helpers ─────────────────────────────────────────
function handleFrom(name: string) {
  return name.toLowerCase().replace(/[^a-z0-9]/g, "").slice(0, 20) || "yourbrand";
}

function initials(name: string) {
  const parts = name.trim().split(/\s+/);
  return ((parts[0]?.[0] ?? "") + (parts[1]?.[0] ?? "")).toUpperCase() || "E";
}

// Deterministic gradient from the text so a given post always looks the same.
function gradient(seed: string) {
  let h = 0;
  for (let i = 0; i < seed.length; i++) h = (h * 31 + seed.charCodeAt(i)) >>> 0;
  const a = h % 360;
  const b = (a + 40 + (h % 60)) % 360;
  return `linear-gradient(135deg, hsl(${a} 70% 52%), hsl(${b} 72% 42%))`;
}

// First emoji in the copy → the hero of the visual; else a channel-appropriate one.
const CHANNEL_EMOJI: Record<string, string> = {
  instagram: "📸", facebook: "👍", linkedin: "💼", x: "🐦", threads: "🧵",
  google_business: "📍", blog: "✍️", email: "✉️", sms: "💬", video: "🎬",
  generic: "✨",
};
function heroEmoji(text: string, channel: string) {
  const m = text.match(
    /(\p{Extended_Pictographic})/u
  );
  return m?.[1] ?? CHANNEL_EMOJI[channel] ?? "✨";
}

function AiVisual({
  text,
  channel,
  aspect,
  isVideo,
  imageUrl,
  videoUrl,
}: {
  text: string;
  channel: string;
  aspect: string;
  isVideo?: boolean;
  imageUrl?: string | null;
  videoUrl?: string | null;
}) {
  // A real generated clip takes over the media slot with native controls.
  if (videoUrl) {
    return (
      <div className={`relative w-full ${aspect} overflow-hidden bg-black`}>
        <video
          src={videoUrl}
          controls
          playsInline
          poster={imageUrl ?? undefined}
          className="absolute inset-0 h-full w-full object-cover"
        />
      </div>
    );
  }
  return (
    <div
      className={`relative w-full ${aspect} overflow-hidden`}
      style={imageUrl ? undefined : { background: gradient(text || channel) }}
    >
      {imageUrl ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={imageUrl}
          alt=""
          className="absolute inset-0 h-full w-full object-cover"
        />
      ) : (
        <>
          <span className="absolute inset-0 grid place-items-center text-6xl drop-shadow">
            {heroEmoji(text, channel)}
          </span>
          <span className="absolute bottom-2 right-2 rounded bg-black/25 px-1.5 py-0.5 text-[9px] font-medium uppercase tracking-wide text-white/90">
            AI visual
          </span>
        </>
      )}
      {isVideo && (
        <span className="absolute inset-0 grid place-items-center">
          <span className="grid h-14 w-14 place-items-center rounded-full bg-black/45 text-2xl text-white backdrop-blur">
            ▶
          </span>
        </span>
      )}
    </div>
  );
}

// The platform's brand mark, shown in the top-left of each preview so it's obvious
// which app a post is styled for. Simplified, recognizable brand badges. Exported
// so the same mark drives the Content platform tabs.
export function PlatformLogo({ channel, size = 22 }: { channel: string; size?: number }) {
  const box = "grid shrink-0 place-items-center rounded-[6px] text-white leading-none";
  const dim = { width: size, height: size };

  if (channel === "instagram") {
    return (
      <span
        className={box}
        style={{
          ...dim,
          background:
            "linear-gradient(45deg,#feda75,#fa7e1e,#d62976,#962fbf,#4f5bd5)",
        }}
        aria-label="Instagram"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.2"
          style={{ width: size * 0.62, height: size * 0.62 }}>
          <rect x="3.5" y="3.5" width="17" height="17" rx="5" />
          <circle cx="12" cy="12" r="4" />
          <circle cx="17.3" cy="6.7" r="1.1" fill="white" stroke="none" />
        </svg>
      </span>
    );
  }
  if (channel === "x") {
    return (
      <span className={box} style={{ ...dim, background: "#000" }} aria-label="X">
        <svg viewBox="0 0 24 24" fill="white" style={{ width: size * 0.58, height: size * 0.58 }}>
          <path d="M18.9 2H22l-7.6 8.7L23 22h-6.8l-5-6.6L5.4 22H2.3l8.2-9.4L1.6 2h7l4.5 6 5.8-6Z" />
        </svg>
      </span>
    );
  }

  const LETTER: Record<string, { bg: string; text: string; el: string }> = {
    facebook: { bg: "#1877F2", text: "italic", el: "f" },
    linkedin: { bg: "#0A66C2", text: "", el: "in" },
    threads: { bg: "#000", text: "", el: "@" },
    google_business: { bg: "#4285F4", text: "", el: "G" },
  };
  const cfg = LETTER[channel];
  if (cfg) {
    return (
      <span
        className={box}
        style={{ ...dim, background: cfg.bg, fontSize: size * (cfg.el.length > 1 ? 0.5 : 0.66), fontStyle: cfg.text === "italic" ? "italic" : "normal", fontWeight: 800 }}
        aria-label={channel}
      >
        {cfg.el}
      </span>
    );
  }

  const emoji: Record<string, string> = { blog: "✍️", email: "✉️", sms: "💬", video: "🎬" };
  return (
    <span className="grid shrink-0 place-items-center rounded-[6px] bg-zinc-200 leading-none"
      style={{ ...dim, fontSize: size * 0.58 }} aria-label={channel}>
      {emoji[channel] ?? "✨"}
    </span>
  );
}

function Avatar({ name, size = 36 }: { name: string; size?: number }) {
  return (
    <span
      className="grid shrink-0 place-items-center rounded-full bg-gradient-to-br from-zinc-500 to-zinc-700 font-semibold text-white"
      style={{ width: size, height: size, fontSize: size * 0.4 }}
    >
      {initials(name)}
    </span>
  );
}

// Tiny inline icons (stroke) so the action rows read as native.
const I = {
  heart: "M12 21s-7.5-4.6-10-9C.6 8.4 2 4 6 4c2 0 3.3 1.2 4 2 .7-.8 2-2 4-2 4 0 5.4 4.4 4 8-2.5 4.4-10 9-10 9z",
  comment: "M21 12a8 8 0 0 1-11.6 7.1L3 21l1.9-6.4A8 8 0 1 1 21 12z",
  share: "M4 12v7a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-7M16 6l-4-4-4 4M12 2v13",
  bookmark: "M6 3h12a1 1 0 0 1 1 1v17l-7-4-7 4V4a1 1 0 0 1 1-1z",
  repost: "M17 1l4 4-4 4M3 11V9a4 4 0 0 1 4-4h14M7 23l-4-4 4-4M21 13v2a4 4 0 0 1-4 4H3",
  send: "M22 2 11 13M22 2l-7 20-4-9-9-4 20-7z",
  like: "M7 22V11M2 13v7a2 2 0 0 0 2 2h13a2 2 0 0 0 2-1.7l1.3-8A2 2 0 0 0 19.3 10H14V5a2 2 0 0 0-2-2l-3 8",
};
function Icon({ d, className = "" }: { d: string; className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
      strokeLinecap="round" strokeLinejoin="round"
      className={`h-[22px] w-[22px] ${className}`}>
      <path d={d} />
    </svg>
  );
}

function Body({ text, channel }: { text: string; channel: string }) {
  // Split trailing hashtag block so we can tint it like the real platforms.
  const tagMatch = text.match(/((?:\s#[\w]+)+)\s*$/);
  const main = tagMatch ? text.slice(0, tagMatch.index).trimEnd() : text;
  const tags = tagMatch ? tagMatch[0].trim() : "";
  const tagColor = channel === "linkedin" || channel === "facebook"
    ? "text-[#1877f2]" : "text-blue-500";
  return (
    <span className="whitespace-pre-wrap">
      {main}
      {tags && <>{"\n"}<span className={tagColor}>{tags}</span></>}
    </span>
  );
}

// ── platform frames ─────────────────────────────────
export function PostPreview({
  channel,
  body,
  business,
  isVideo,
  imageUrl,
  videoUrl,
}: {
  channel: string;
  body: string;
  business: string;
  isVideo?: boolean;
  imageUrl?: string | null;
  videoUrl?: string | null;
}) {
  const handle = handleFrom(business);
  const shell =
    "mx-auto w-full max-w-[400px] overflow-hidden rounded-xl border border-border bg-white text-[13px] text-zinc-900 shadow-sm";
  const video = isVideo || channel === "video";

  if (channel === "instagram") {
    return (
      <div className={shell}>
        <div className="flex items-center gap-2 px-3 py-2.5">
          <PlatformLogo channel={channel} />
          <Avatar name={business} size={32} />
          <span className="font-semibold">{handle}</span>
          <span className="ml-auto text-lg leading-none text-zinc-500">⋯</span>
        </div>
        <AiVisual text={body} channel={channel} aspect="aspect-square" isVideo={video} imageUrl={imageUrl} videoUrl={videoUrl} />
        <div className="flex items-center gap-4 px-3 pt-2.5 text-zinc-800">
          <Icon d={I.heart} /><Icon d={I.comment} /><Icon d={I.send} />
          <Icon d={I.bookmark} className="ml-auto" />
        </div>
        <p className="px-3 py-1 font-semibold">1,248 likes</p>
        <p className="px-3 pb-3 leading-snug">
          <span className="font-semibold">{handle}</span>{" "}
          <Body text={body} channel={channel} />
        </p>
      </div>
    );
  }

  if (channel === "x" || channel === "threads") {
    return (
      <div className={`${shell} px-3.5 py-3`}>
        <div className="flex gap-3">
          <PlatformLogo channel={channel} />
          <Avatar name={business} size={40} />
          <div className="min-w-0 flex-1">
            <p className="flex items-center gap-1">
              <span className="font-bold">{business}</span>
              {channel === "x" && <span className="text-zinc-500">✓</span>}
              <span className="truncate text-zinc-500">@{handle} · 2h</span>
              <span className="ml-auto text-zinc-500">⋯</span>
            </p>
            <p className="mt-1 leading-snug">
              <Body text={body} channel={channel} />
            </p>
            <div className="mt-3 overflow-hidden rounded-2xl border border-zinc-200">
              <AiVisual text={body} channel={channel} aspect="aspect-video" isVideo={video} imageUrl={imageUrl} videoUrl={videoUrl} />
            </div>
            <div className="mt-2.5 flex max-w-[320px] items-center justify-between text-zinc-500">
              <Icon d={I.comment} className="h-[18px] w-[18px]" />
              <Icon d={I.repost} className="h-[18px] w-[18px]" />
              <Icon d={I.heart} className="h-[18px] w-[18px]" />
              <Icon d={I.share} className="h-[18px] w-[18px]" />
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (channel === "linkedin") {
    return (
      <div className={shell}>
        <div className="flex items-center gap-2 px-3 py-2.5">
          <PlatformLogo channel={channel} />
          <Avatar name={business} size={44} />
          <div className="min-w-0">
            <p className="font-semibold leading-tight">{business}</p>
            <p className="truncate text-xs text-zinc-500">Sponsored · 🌐</p>
          </div>
        </div>
        <p className="px-3 pb-2 leading-snug"><Body text={body} channel={channel} /></p>
        <AiVisual text={body} channel={channel} aspect="aspect-video" isVideo={video} imageUrl={imageUrl} videoUrl={videoUrl} />
        <div className="grid grid-cols-4 gap-1 px-2 py-1.5 text-xs font-medium text-zinc-600">
          {[["like", "Like"], ["comment", "Comment"], ["repost", "Repost"], ["send", "Send"]].map(
            ([k, label]) => (
              <span key={label} className="flex items-center justify-center gap-1.5 py-1">
                <Icon d={(I as Record<string, string>)[k]} className="h-4 w-4" /> {label}
              </span>
            )
          )}
        </div>
      </div>
    );
  }

  if (channel === "facebook") {
    return (
      <div className={shell}>
        <div className="flex items-center gap-2 px-3 py-2.5">
          <PlatformLogo channel={channel} />
          <Avatar name={business} size={40} />
          <div>
            <p className="font-semibold leading-tight">{business}</p>
            <p className="text-xs text-zinc-500">2h · 🌐</p>
          </div>
        </div>
        <p className="px-3 pb-2 leading-snug"><Body text={body} channel={channel} /></p>
        <AiVisual text={body} channel={channel} aspect="aspect-video" isVideo={video} imageUrl={imageUrl} videoUrl={videoUrl} />
        <div className="grid grid-cols-3 border-t border-zinc-200 py-1 text-sm font-medium text-zinc-600">
          {[["like", "Like"], ["comment", "Comment"], ["share", "Share"]].map(([k, label]) => (
            <span key={label} className="flex items-center justify-center gap-1.5 py-1.5">
              <Icon d={(I as Record<string, string>)[k]} className="h-[18px] w-[18px]" /> {label}
            </span>
          ))}
        </div>
      </div>
    );
  }

  // Generic (google_business / blog / email / sms / video / other)
  return (
    <div className={shell}>
      <div className="flex items-center gap-2 px-3 py-2.5">
        <PlatformLogo channel={channel} />
        <Avatar name={business} size={36} />
        <span className="font-semibold">{business}</span>
      </div>
      <AiVisual text={body} channel={channel} aspect="aspect-video" isVideo={video} imageUrl={imageUrl} videoUrl={videoUrl} />
      <p className="px-3 py-3 leading-snug"><Body text={body} channel={channel} /></p>
    </div>
  );
}

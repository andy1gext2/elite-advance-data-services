"use client";

import { use, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import {
  CHANNELS,
  CHANNEL_LABELS,
  channelRank,
  type Asset,
  type Business,
  type ContentItem,
  type Timeframe,
} from "@/lib/types";
import { PlatformLogo, PostPreview } from "@/components/PostPreview";
import { PostEditModal } from "@/components/PostEditModal";
import { VideoButton } from "@/components/VideoButton";
import { CampaignStartCalendar } from "@/components/CampaignStartCalendar";
import { CustomizedMediaCard } from "@/components/CustomizedMediaCard";
import { ProgressBar, useEstimatedProgress } from "@/components/Progress";
import {
  Alert,
  Badge,
  Button,
  Card,
  Field,
  PageHeader,
  Textarea,
} from "@/components/ui";

const STATUS_TONE: Record<string, "green" | "red" | "amber" | "default"> = {
  approved: "green",
  rejected: "red",
  draft: "amber",
};

// Campaign length the user picks in the content builder.
const DURATIONS: { value: Timeframe; label: string; hint: string }[] = [
  { value: "day", label: "One day", hint: "All platforms at once, today" },
  { value: "week", label: "One week", hint: "All platforms, every other day for a week" },
  { value: "month", label: "One month", hint: "All platforms, every other day for a month" },
];

function todayISO() {
  const n = new Date();
  const p = (x: number) => String(x).padStart(2, "0");
  return `${n.getFullYear()}-${p(n.getMonth() + 1)}-${p(n.getDate())}`;
}

function addDaysISO(iso: string, n: number) {
  const [y, m, d] = iso.split("-").map(Number);
  const dt = new Date(y, m - 1, d);
  dt.setDate(dt.getDate() + n);
  const p = (x: number) => String(x).padStart(2, "0");
  return `${dt.getFullYear()}-${p(dt.getMonth() + 1)}-${p(dt.getDate())}`;
}

function fmtShort(iso: string) {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

// A scheduled post's publish date: "Today · Jul 12" when it's today, else the date.
function fmtPublish(iso: string) {
  const [y, m, d] = iso.split("T")[0].split("-").map(Number);
  const dt = new Date(y, m - 1, d);
  const now = new Date();
  const isToday =
    y === now.getFullYear() && m - 1 === now.getMonth() && d === now.getDate();
  const label = dt.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
  return isToday ? `Today · ${label}` : label;
}

export default function ContentPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [business, setBusiness] = useState<Business | null>(null);
  const [items, setItems] = useState<ContentItem[]>([]);
  const [assets, setAssets] = useState<Asset[]>([]);
  // content_item_id -> scheduled publish date (from the campaign calendar).
  const [publishAt, setPublishAt] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  // Campaign builder.
  const [brief, setBrief] = useState("");
  const [productId, setProductId] = useState("");
  const [duration, setDuration] = useState<Timeframe>("day");
  const [startDate, setStartDate] = useState(todayISO());
  const [calOpen, setCalOpen] = useState(false);
  const [notice, setNotice] = useState("");

  // Prefill the brief when arriving from a dashboard trend suggestion.
  useEffect(() => {
    const raw = sessionStorage.getItem("draftBrief");
    if (!raw) return;
    sessionStorage.removeItem("draftBrief");
    try {
      const { brief: b } = JSON.parse(raw) as { brief?: string };
      if (b) {
        setBrief(b);
        setNotice("Prefilled from a trending suggestion — pick a duration and generate.");
      }
    } catch {
      /* ignore malformed */
    }
  }, []);

  // Rough per-timeframe estimate: a month drafts ~30 posts, a week ~15, a day ~5.
  const campaignPct = useEstimatedProgress(
    busy,
    duration === "day" ? 12000 : duration === "week" ? 35000 : 70000
  );

  const campaignSpan = duration === "day" ? 1 : duration === "week" ? 7 : 30;
  const rangeLabel =
    campaignSpan === 1
      ? fmtShort(startDate)
      : `${fmtShort(startDate)} – ${fmtShort(addDaysISO(startDate, campaignSpan - 1))}`;

  // Group the (already popularity-sorted) posts by platform — one card per platform.
  const groups = useMemo(() => {
    const map = new Map<string, ContentItem[]>();
    for (const it of items) {
      const arr = map.get(it.channel) ?? [];
      arr.push(it);
      map.set(it.channel, arr);
    }
    return [...map.entries()].map(([channel, posts]) => ({ channel, posts }));
  }, [items]);

  // Platform filter (server-side); the queue always shows drafts awaiting review.
  const [channelFilter, setChannelFilter] = useState("");
  const [flash, setFlash] = useState("");

  // The post currently open in the edit modal.
  const [editing, setEditing] = useState<ContentItem | null>(null);

  const loadItems = useCallback(async () => {
    // Only draft posts appear here — approved ones move to the calendar, rejected
    // ones are deleted.
    const content = await api.listContent(id, {
      status: "draft",
      channel: channelFilter || undefined,
    });
    // Most-popular platforms (Instagram, Facebook, X…) first; recency within each.
    setItems(
      [...content].sort((a, b) => channelRank(a.channel) - channelRank(b.channel))
    );
  }, [id, channelFilter]);

  // Map each campaign post to its scheduled publish date.
  const loadCalendar = useCallback(async () => {
    const cal = await api.campaignCalendar(id).catch(() => []);
    const map: Record<string, string> = {};
    for (const e of cal) {
      if (e.content_item_id) map[e.content_item_id] = e.scheduled_at;
    }
    setPublishAt(map);
  }, [id]);

  // Business + product assets + publish dates once; items whenever filters change.
  useEffect(() => {
    api.getBusiness(id).then(setBusiness).catch(() => {});
    api.listAssets(id).then(setAssets).catch(() => {});
    loadCalendar().catch(() => {});
  }, [id, loadCalendar]);

  useEffect(() => {
    loadItems().catch((e) =>
      setError(e instanceof ApiError ? e.message : "Failed to load")
    );
  }, [loadItems]);

  async function onCreateCampaign(e: React.FormEvent) {
    e.preventDefault();
    if (!brief.trim()) return;
    setError("");
    setNotice("");
    setBusy(true);
    try {
      const camp = await api.proposeCampaign(
        id,
        brief.trim(),
        duration,
        productId || undefined,
        startDate
      );
      const product = assets.find((a) => a.id === productId);
      const label = DURATIONS.find((d) => d.value === duration)?.label ?? duration;
      setBrief("");
      setFlash("");
      setNotice(
        `Drafted a ${label.toLowerCase()} campaign` +
          (product ? ` promoting ${product.name ?? product.filename}` : "") +
          ` — ${camp.items.length} posts. Review them below, then see the schedule in Calendar.`
      );
      // Show the fresh drafts regardless of any active platform filter.
      setChannelFilter("");
      await Promise.all([loadItems(), loadCalendar()]);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Campaign generation failed");
    } finally {
      setBusy(false);
    }
  }

  function replaceItem(updated: ContentItem) {
    // Keep the queue to drafts only (an edit that leaves draft drops out of view).
    setItems((list) =>
      list
        .map((it) => (it.id === updated.id ? updated : it))
        .filter((it) => it.status === "draft")
    );
  }

  async function decide(item: ContentItem, approve: boolean) {
    setError("");
    try {
      if (approve) {
        await api.approve(id, item.id);
        setFlash("✓ Approved — booked on your calendar.");
        loadCalendar().catch(() => {});
      } else {
        await api.deleteContent(id, item.id);
        setFlash("🗑 Post deleted.");
      }
      // Decided posts leave the review queue.
      setItems((list) => list.filter((it) => it.id !== item.id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Update failed");
    }
  }

  return (
    <>
      <PageHeader
        title="Content studio"
        subtitle="Pick a product, choose how long to promote it, and the AI drafts a whole campaign — platform-tailored posts you can edit, approve, and schedule."
      />

      <Card className="mt-6">
        <form onSubmit={onCreateCampaign} className="space-y-5">
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Promote a product or service">
              <select
                value={productId}
                onChange={(e) => setProductId(e.target.value)}
                className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-fg outline-none focus:border-brand focus:ring-2 focus:ring-brand/30"
              >
                <option value="">General campaign — nothing specific</option>
                {assets.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.kind === "service" ? "🛠 " : "📦 "}
                    {a.name ?? a.filename}
                  </option>
                ))}
              </select>
              {assets.length === 0 && (
                <p className="mt-1 text-xs text-muted">
                  Nothing added yet —{" "}
                  <Link href={`/businesses/${id}/products`} className="text-brand hover:underline">
                    add a product or service
                  </Link>{" "}
                  so the AI can build campaigns around it.
                </p>
              )}
            </Field>

            <div>
              <span className="mb-1.5 block text-sm font-medium text-fg">
                How long to promote it
              </span>
              <div className="flex flex-wrap gap-2">
                {DURATIONS.map((d) => (
                  <button
                    key={d.value}
                    type="button"
                    onClick={() => setDuration(d.value)}
                    title={d.hint}
                    className={
                      "rounded-lg border px-3 py-2 text-sm font-medium transition-colors " +
                      (duration === d.value
                        ? "border-brand bg-brand/10 text-brand"
                        : "border-border text-muted hover:text-fg")
                    }
                  >
                    {d.label}
                  </button>
                ))}
              </div>
              <p className="mt-1.5 text-xs text-muted">
                {DURATIONS.find((d) => d.value === duration)?.hint}
              </p>
              <button
                type="button"
                onClick={() => setCalOpen((o) => !o)}
                className="mt-2 inline-flex items-center gap-2 rounded-lg border border-border px-3 py-1.5 text-sm transition-colors hover:border-brand"
              >
                <span>📅</span>
                <span className="font-medium">{rangeLabel}</span>
                <span className="text-xs text-muted">{calOpen ? "▲" : "▼"}</span>
              </button>
            </div>
          </div>

          {calOpen && (
            <CampaignStartCalendar
              value={startDate}
              onChange={(d) => {
                setStartDate(d);
                setCalOpen(false);
              }}
              spanDays={campaignSpan}
            />
          )}

          <Field label="Campaign focus / brief">
            <Textarea
              rows={3}
              value={brief}
              onChange={(e) => setBrief(e.target.value)}
              placeholder="Highlight the bright, citrusy flavor and small-batch sourcing — drive weekend pour-over sales."
            />
          </Field>
          {notice && (
            <p className="rounded-lg border border-brand/30 bg-brand/10 px-3 py-2 text-sm text-brand">
              {notice}
            </p>
          )}
          <Alert>{error}</Alert>
          {busy && <ProgressBar percent={campaignPct} label="Drafting your campaign…" />}
          <div className="flex justify-end">
            <Button type="submit" loading={busy} disabled={!brief.trim()}>
              {busy ? "Drafting campaign…" : "Generate campaign"}
            </Button>
          </div>
        </form>
      </Card>

      <CustomizedMediaCard
        businessId={id}
        mediaAssets={assets.filter((a) => a.kind === "media")}
        onPosted={loadItems}
      />

      {/* Review queue header */}
      <div className="mt-8">
        <h2 className="text-lg font-semibold">
          Review queue <span className="text-muted">({items.length})</span>
        </h2>
        <p className="text-xs text-muted">
          Approve to book it on the calendar · reject to delete it.
        </p>
      </div>

      {/* Flip through the per-platform sections */}
      <PlatformTabs value={channelFilter} onChange={setChannelFilter} />

      {flash && (
        <p className="mt-3 rounded-lg border border-brand/30 bg-brand/10 px-3 py-2 text-sm text-brand">
          {flash}
        </p>
      )}

      {items.length === 0 ? (
        <p className="mt-4 text-sm text-muted">
          {channelFilter
            ? "No posts to review on this platform."
            : "No posts to review — draft a campaign above."}
        </p>
      ) : (
        <div className="mt-4 grid gap-4">
          {groups.map((g) => (
            <PlatformGroup
              key={g.channel}
              channel={g.channel}
              posts={g.posts}
              businessId={id}
              businessName={business?.name ?? "Your Brand"}
              assets={assets}
              publishAt={publishAt}
              defaultProductId={productId}
              onDecide={decide}
              onEdit={setEditing}
              onSaved={replaceItem}
              onError={setError}
            />
          ))}
        </div>
      )}

      {editing && (
        <PostEditModal
          businessId={id}
          post={{
            id: editing.id,
            title: editing.title,
            body: editing.body,
            channel: editing.channel,
            content_type: editing.content_type,
            image_url: editing.image_url,
            video_url: editing.video_url,
          }}
          businessName={business?.name ?? "Your Brand"}
          assets={assets}
          defaultProductId={productId}
          onClose={() => setEditing(null)}
          onSaved={replaceItem}
        />
      )}
    </>
  );
}

// A flip-through row of platform sections: "All" + one tab per platform (popularity
// order). The ‹ › arrows step through platforms so you can page across sections.
function PlatformTabs({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  const order = ["", ...CHANNELS];
  function flip(dir: number) {
    const i = Math.max(0, order.indexOf(value));
    onChange(order[(i + dir + order.length) % order.length]);
  }
  return (
    <div className="mt-4 flex items-center gap-2">
      <button
        type="button"
        onClick={() => flip(-1)}
        aria-label="Previous platform"
        className="shrink-0 rounded-lg border border-border px-2 py-1.5 text-sm text-muted hover:text-fg"
      >
        ‹
      </button>
      <div className="flex flex-1 gap-1.5 overflow-x-auto pb-1">
        <Tab active={value === ""} onClick={() => onChange("")}>
          <span className="grid h-4 w-4 place-items-center rounded bg-brand text-[9px] text-brand-fg">
            ★
          </span>
          All
        </Tab>
        {CHANNELS.map((c) => (
          <Tab key={c} active={value === c} onClick={() => onChange(c)}>
            <PlatformLogo channel={c} size={16} />
            {CHANNEL_LABELS[c] ?? c}
          </Tab>
        ))}
      </div>
      <button
        type="button"
        onClick={() => flip(1)}
        aria-label="Next platform"
        className="shrink-0 rounded-lg border border-border px-2 py-1.5 text-sm text-muted hover:text-fg"
      >
        ›
      </button>
    </div>
  );
}

function Tab({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={
        "flex shrink-0 items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm font-medium capitalize transition-colors " +
        (active
          ? "border-brand bg-brand/10 text-brand"
          : "border-border text-muted hover:text-fg")
      }
    >
      {children}
    </button>
  );
}

// One card per platform: the posts for that platform, shown one at a time with
// ‹ › arrows to page through them. Keeps the review queue concise.
function PlatformGroup({
  channel,
  posts,
  businessId,
  businessName,
  assets,
  publishAt,
  defaultProductId,
  onDecide,
  onEdit,
  onSaved,
  onError,
}: {
  channel: string;
  posts: ContentItem[];
  businessId: string;
  businessName: string;
  assets: Asset[];
  publishAt: Record<string, string>;
  defaultProductId: string;
  onDecide: (item: ContentItem, approve: boolean) => void | Promise<void>;
  onEdit: (item: ContentItem) => void;
  onSaved: (updated: ContentItem) => void;
  onError: (msg: string) => void;
}) {
  // Order posts by publish date ascending — page 1 = campaign start, last = end.
  const ordered = useMemo(
    () =>
      [...posts].sort((a, b) =>
        (publishAt[a.id] ?? "~").localeCompare(publishAt[b.id] ?? "~")
      ),
    [posts, publishAt]
  );
  const [index, setIndex] = useState(0);
  useEffect(() => {
    if (index > ordered.length - 1) setIndex(Math.max(0, ordered.length - 1));
  }, [ordered.length, index]);
  const cur = Math.min(index, ordered.length - 1);
  const post = ordered[cur];
  if (!post) return null;

  return (
    <Card className="space-y-3 overflow-hidden">
      <div className="flex items-center gap-2 border-b border-border pb-3">
        <PlatformLogo channel={channel} size={22} />
        <span className="font-semibold">{CHANNEL_LABELS[channel] ?? channel}</span>
        <span className="text-sm text-muted">({ordered.length})</span>
        {ordered.length > 1 && (
          <span className="ml-auto flex items-center gap-2">
            <button
              type="button"
              onClick={() => setIndex((i) => Math.max(0, i - 1))}
              disabled={cur === 0}
              aria-label="Previous post"
              className="rounded-md border border-border px-2 py-1 text-sm text-muted hover:text-fg disabled:opacity-40"
            >
              ‹
            </button>
            <span className="text-xs tabular-nums text-muted">
              {cur + 1} / {ordered.length}
            </span>
            <button
              type="button"
              onClick={() => setIndex((i) => Math.min(ordered.length - 1, i + 1))}
              disabled={cur >= ordered.length - 1}
              aria-label="Next post"
              className="rounded-md border border-border px-2 py-1 text-sm text-muted hover:text-fg disabled:opacity-40"
            >
              ›
            </button>
          </span>
        )}
      </div>
      <PostContent
        key={post.id}
        item={post}
        businessId={businessId}
        businessName={businessName}
        assets={assets}
        publishAt={publishAt[post.id]}
        defaultProductId={defaultProductId}
        onDecide={onDecide}
        onEdit={onEdit}
        onSaved={onSaved}
        onError={onError}
      />
    </Card>
  );
}

function PostContent({
  item,
  businessId,
  businessName,
  assets,
  publishAt,
  defaultProductId,
  onDecide,
  onEdit,
  onSaved,
  onError,
}: {
  item: ContentItem;
  businessId: string;
  businessName: string;
  assets: Asset[];
  publishAt?: string;
  defaultProductId: string;
  onDecide: (item: ContentItem, approve: boolean) => void | Promise<void>;
  onEdit: (item: ContentItem) => void;
  onSaved: (updated: ContentItem) => void;
  onError: (msg: string) => void;
}) {
  const [imaging, setImaging] = useState(false);
  const [videoRendering, setVideoRendering] = useState(false);
  // One shared progress bar for whichever generation is running (only one at a
  // time). Image ≈ 9s, video ≈ 75s.
  const generating = imaging || videoRendering;
  const genPct = useEstimatedProgress(generating, imaging ? 9000 : 75000);
  // Image-grounding product: the post's own campaign product wins, else the one
  // picked in the studio — so a product post's image always features that product.
  const [productId, setProductId] = useState(item.product_asset_id ?? defaultProductId);
  useEffect(
    () => setProductId(item.product_asset_id ?? defaultProductId),
    [defaultProductId, item.product_asset_id]
  );
  // Swipe feedback: reject slides left, approve slides right with a green glow.
  const [anim, setAnim] = useState<"" | "approve" | "reject">("");

  // Reset once the decision lands (the item's status changes) so the card settles.
  useEffect(() => setAnim(""), [item.status]);

  async function act(approve: boolean) {
    if (anim) return;
    setAnim(approve ? "approve" : "reject");
    await new Promise((r) => setTimeout(r, 320)); // let the swipe play
    await onDecide(item, approve);
    setAnim("");
  }

  async function makeImage() {
    setImaging(true);
    try {
      onSaved(await api.generateImage(businessId, item.id, productId || undefined));
    } catch (err) {
      onError(err instanceof ApiError ? err.message : "Image generation failed");
    } finally {
      setImaging(false);
    }
  }

  return (
    <div
      className={
        "space-y-3 transition-all duration-300 ease-out " +
        (anim === "reject"
          ? "-translate-x-[110%] opacity-0 ring-1 ring-red-400/50"
          : anim === "approve"
          ? "translate-x-[110%] opacity-0 ring-2 ring-green-500 bg-green-500/10"
          : "")
      }
    >
      <div className="flex flex-wrap items-center gap-2">
        <Badge>{item.content_type.replace(/_/g, " ")}</Badge>
        {publishAt && (
          <span className="inline-flex items-center gap-1 rounded-full border border-border bg-bg px-2 py-0.5 text-xs font-medium text-muted">
            📅 {fmtPublish(publishAt)}
          </span>
        )}
        {/* Shared generation progress — fills the space to the left of the status. */}
        {generating ? (
          <div className="ml-auto flex min-w-[120px] flex-1 items-center gap-2">
            <ProgressBar percent={genPct} />
            <span className="shrink-0 text-[11px] tabular-nums text-muted">
              {Math.round(genPct)}%
            </span>
          </div>
        ) : (
          <span className="ml-auto" />
        )}
        <Badge tone={STATUS_TONE[item.status] ?? "default"}>{item.status}</Badge>
      </div>

      <div className="grid gap-5 md:grid-cols-2">
        {/* Copy + actions */}
        <div className="flex flex-col">
          {item.title && <p className="font-medium">{item.title}</p>}
          <p className="whitespace-pre-wrap text-sm text-fg/90">{item.body}</p>
          <div className="mt-auto flex justify-end gap-2 border-t border-border pt-3">
            <Button variant="secondary" onClick={() => onEdit(item)}>
              ✎ Edit
            </Button>
            <Button
              variant="danger"
              onClick={() => act(false)}
              disabled={item.status === "rejected" || anim !== ""}
            >
              Reject
            </Button>
            <Button
              onClick={() => act(true)}
              disabled={item.status === "approved" || anim !== ""}
            >
              Approve
            </Button>
          </div>
        </div>

        {/* Platform preview + image controls (top-right) */}
        <div>
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
            <p className="text-xs font-medium uppercase tracking-wide text-muted">
              Preview
            </p>
            <div className="flex items-center gap-2">
              {assets.length > 0 && (
                <select
                  value={productId}
                  onChange={(e) => setProductId(e.target.value)}
                  title="Base the image on a product photo"
                  className="max-w-[140px] rounded-lg border border-border bg-bg px-2 py-1.5 text-xs text-fg outline-none focus:border-brand"
                >
                  <option value="">No product</option>
                  {assets.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.name ?? a.filename}
                    </option>
                  ))}
                </select>
              )}
              <Button variant="ghost" onClick={makeImage} loading={imaging}>
                {item.image_url ? "🖼 Regenerate" : "🖼 Generate image"}
              </Button>
              <VideoButton
                businessId={businessId}
                itemId={item.id}
                hasVideo={Boolean(item.video_url)}
                onDone={(url) => onSaved({ ...item, video_url: url })}
                onError={onError}
                onRenderingChange={setVideoRendering}
              />
            </div>
          </div>
          <PostPreview
            channel={item.channel}
            body={item.body}
            business={businessName}
            isVideo={item.content_type === "video_script"}
            imageUrl={item.image_url}
            videoUrl={item.video_url}
          />
        </div>
      </div>
    </div>
  );
}

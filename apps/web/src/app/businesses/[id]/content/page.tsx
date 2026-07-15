"use client";

import { use, useCallback, useEffect, useState } from "react";
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
  const [notice, setNotice] = useState("");

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
        productId || undefined
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
            <Field label="Promote a product">
              <select
                value={productId}
                onChange={(e) => setProductId(e.target.value)}
                className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-fg outline-none focus:border-brand focus:ring-2 focus:ring-brand/30"
              >
                <option value="">No product — general campaign</option>
                {assets.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name ?? a.filename}
                  </option>
                ))}
              </select>
              {assets.length === 0 && (
                <p className="mt-1 text-xs text-muted">
                  No products yet —{" "}
                  <Link href={`/businesses/${id}/products`} className="text-brand hover:underline">
                    add one
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
            </div>
          </div>

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
          <div className="flex justify-end">
            <Button type="submit" loading={busy} disabled={!brief.trim()}>
              {busy ? "Drafting campaign…" : "Generate campaign"}
            </Button>
          </div>
        </form>
      </Card>

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
        <div className="mt-4 grid gap-4 overflow-hidden">
          {items.map((item) => (
            <ContentCard
              key={item.id}
              item={item}
              businessId={id}
              businessName={business?.name ?? "Your Brand"}
              assets={assets}
              publishAt={publishAt[item.id]}
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

function ContentCard({
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
  // Image-grounding product defaults to (and follows) the one picked in the studio.
  const [productId, setProductId] = useState(defaultProductId);
  useEffect(() => setProductId(defaultProductId), [defaultProductId]);
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
    <Card
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
        <Badge tone="brand">
          {CHANNEL_LABELS[item.channel] ?? item.channel}
        </Badge>
        <Badge>{item.content_type.replace(/_/g, " ")}</Badge>
        {publishAt && (
          <span className="inline-flex items-center gap-1 rounded-full border border-border bg-bg px-2 py-0.5 text-xs font-medium text-muted">
            📅 {fmtPublish(publishAt)}
          </span>
        )}
        <span className="ml-auto" />
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
              {CHANNEL_LABELS[item.channel] ?? item.channel} preview
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
    </Card>
  );
}

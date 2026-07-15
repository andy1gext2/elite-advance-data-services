"use client";

import { use, useCallback, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import {
  CHANNEL_LABELS,
  type AutopilotConfig,
  type Campaign,
  type CampaignDetail,
  type CampaignItem,
  type ContentItem,
  type Timeframe,
} from "@/lib/types";
import { PostEditModal } from "@/components/PostEditModal";
import { Alert, Badge, Button, Card, Field, Input, PageHeader, Textarea } from "@/components/ui";

const TIMEFRAMES: Timeframe[] = ["week", "month", "quarter", "year"];
const STATUS_TONE: Record<string, "amber" | "green" | "red" | "default"> = {
  proposed: "amber",
  scheduled: "green",
  rejected: "red",
};

export default function CampaignsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [error, setError] = useState("");

  const loadCampaigns = useCallback(async () => {
    setCampaigns(await api.listCampaigns(id));
  }, [id]);

  useEffect(() => {
    loadCampaigns().catch((e) =>
      setError(e instanceof ApiError ? e.message : "Failed to load")
    );
  }, [loadCampaigns]);

  return (
    <>
      <PageHeader
        title="Campaigns"
        subtitle="Let AI draft whole campaigns — a plan plus the content — for your one-tap approval. Nothing publishes until you say so."
      />

      <div className="mt-4">
        <Alert>{error}</Alert>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <AutopilotCard businessId={id} onError={setError} />
        <ProposeCard
          businessId={id}
          onProposed={loadCampaigns}
          onError={setError}
        />
      </div>

      <h2 className="mt-10 text-lg font-semibold">
        Your campaigns <span className="text-muted">({campaigns.length})</span>
      </h2>
      {campaigns.length === 0 ? (
        <p className="mt-3 text-sm text-muted">
          No campaigns yet — draft one above, or enable autopilot.
        </p>
      ) : (
        <div className="mt-4 grid gap-4">
          {campaigns.map((c) => (
            <CampaignCard
              key={c.id}
              businessId={id}
              campaign={c}
              onChanged={loadCampaigns}
              onError={setError}
            />
          ))}
        </div>
      )}
    </>
  );
}

function AutopilotCard({
  businessId,
  onError,
}: {
  businessId: string;
  onError: (m: string) => void;
}) {
  const [cfg, setCfg] = useState<AutopilotConfig | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api.getAutopilot(businessId).then(setCfg).catch(() => {});
  }, [businessId]);

  async function save() {
    if (!cfg) return;
    setSaving(true);
    setSaved(false);
    try {
      setCfg(await api.setAutopilot(businessId, cfg));
      setSaved(true);
    } catch (err) {
      onError(err instanceof ApiError ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  if (!cfg) return <Card>Loading…</Card>;

  return (
    <Card>
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="font-semibold">Autopilot</h2>
          <p className="mt-1 text-xs text-muted">
            Automatically draft a campaign on a schedule, ready for your approval.
          </p>
        </div>
        <label className="inline-flex cursor-pointer items-center gap-2">
          <input
            type="checkbox"
            className="h-4 w-4"
            checked={cfg.autopilot_enabled}
            onChange={(e) =>
              setCfg({ ...cfg, autopilot_enabled: e.target.checked })
            }
          />
          <span className="text-sm font-medium">
            {cfg.autopilot_enabled ? "On" : "Off"}
          </span>
        </label>
      </div>

      <div className="mt-4 space-y-3">
        <Field label="Campaign theme" hint="Leave blank to use your business goals.">
          <Textarea
            rows={2}
            value={cfg.autopilot_theme ?? ""}
            onChange={(e) => setCfg({ ...cfg, autopilot_theme: e.target.value })}
            placeholder="Seasonal promotions, community stories, product education…"
          />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Every (days)">
            <Input
              type="number"
              min={1}
              max={90}
              value={cfg.autopilot_frequency_days}
              onChange={(e) =>
                setCfg({
                  ...cfg,
                  autopilot_frequency_days: Number(e.target.value) || 7,
                })
              }
            />
          </Field>
          <Field label="Plan length">
            <select
              value={cfg.autopilot_timeframe}
              onChange={(e) =>
                setCfg({ ...cfg, autopilot_timeframe: e.target.value })
              }
              className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm capitalize text-fg outline-none focus:border-brand focus:ring-2 focus:ring-brand/30"
            >
              {TIMEFRAMES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </Field>
        </div>
        {cfg.autopilot_last_run_at && (
          <p className="text-xs text-muted">
            Last drafted:{" "}
            {new Date(cfg.autopilot_last_run_at).toLocaleString()}
          </p>
        )}
        <div className="flex items-center justify-end gap-3">
          {saved && <span className="text-xs text-green-600 dark:text-green-500">Saved ✓</span>}
          <Button onClick={save} loading={saving}>
            Save autopilot
          </Button>
        </div>
      </div>
    </Card>
  );
}

function ProposeCard({
  businessId,
  onProposed,
  onError,
}: {
  businessId: string;
  onProposed: () => void;
  onError: (m: string) => void;
}) {
  const [theme, setTheme] = useState("");
  const [timeframe, setTimeframe] = useState<Timeframe>("week");
  const [busy, setBusy] = useState(false);

  async function propose(e: React.FormEvent) {
    e.preventDefault();
    if (!theme.trim()) return;
    setBusy(true);
    try {
      await api.proposeCampaign(businessId, theme.trim(), timeframe);
      setTheme("");
      onProposed();
    } catch (err) {
      onError(err instanceof ApiError ? err.message : "Could not draft campaign");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <h2 className="font-semibold">Draft a campaign now</h2>
      <p className="mt-1 text-xs text-muted">
        The AI plans the posts and writes the content. You review before anything
        is scheduled.
      </p>
      <form onSubmit={propose} className="mt-4 space-y-3">
        <Field label="Theme / goal">
          <Textarea
            rows={2}
            value={theme}
            onChange={(e) => setTheme(e.target.value)}
            placeholder="Fall seasonal menu — pumpkin drinks, cozy vibes, loyalty rewards."
          />
        </Field>
        <div className="flex items-end justify-between gap-3">
          <Field label="Plan length">
            <select
              value={timeframe}
              onChange={(e) => setTimeframe(e.target.value as Timeframe)}
              className="rounded-lg border border-border bg-bg px-3 py-2 text-sm capitalize text-fg outline-none focus:border-brand focus:ring-2 focus:ring-brand/30"
            >
              {TIMEFRAMES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </Field>
          <Button type="submit" loading={busy} disabled={!theme.trim()}>
            {busy ? "Drafting…" : "Draft campaign"}
          </Button>
        </div>
      </form>
    </Card>
  );
}

function CampaignCard({
  businessId,
  campaign,
  onChanged,
  onError,
}: {
  businessId: string;
  campaign: Campaign;
  onChanged: () => void;
  onError: (m: string) => void;
}) {
  const [detail, setDetail] = useState<CampaignDetail | null>(null);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState<"approve" | "reject" | null>(null);
  const [editing, setEditing] = useState<CampaignItem | null>(null);

  // Reflect an edited post back into the expanded campaign view.
  function onPostSaved(updated: ContentItem) {
    setDetail((d) =>
      d
        ? {
            ...d,
            items: d.items.map((x) =>
              x.content_item_id === updated.id
                ? { ...x, title: updated.title, body: updated.body }
                : x
            ),
          }
        : d
    );
  }

  async function toggle() {
    const next = !open;
    setOpen(next);
    if (next && !detail) {
      try {
        setDetail(await api.getCampaign(businessId, campaign.id));
      } catch (err) {
        onError(err instanceof ApiError ? err.message : "Failed to load");
      }
    }
  }

  async function act(kind: "approve" | "reject") {
    setBusy(kind);
    try {
      const updated =
        kind === "approve"
          ? await api.approveCampaign(businessId, campaign.id)
          : await api.rejectCampaign(businessId, campaign.id);
      setDetail(updated);
      onChanged();
    } catch (err) {
      onError(err instanceof ApiError ? err.message : "Action failed");
    } finally {
      setBusy(null);
    }
  }

  const status = detail?.status ?? campaign.status;

  return (
    <Card className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        {campaign.source === "autopilot" && <Badge tone="brand">✨ autopilot</Badge>}
        <span className="font-medium">{campaign.name}</span>
        <span className="text-xs text-muted">· {campaign.timeframe}</span>
        <span className="ml-auto" />
        <Badge tone={STATUS_TONE[status] ?? "default"}>{status}</Badge>
        <Button variant="ghost" onClick={toggle}>
          {open ? "Hide" : "Review"}
        </Button>
      </div>

      {open && (
        <div className="space-y-3 border-t border-border pt-3">
          {!detail ? (
            <p className="text-sm text-muted">Loading…</p>
          ) : (
            <>
              <div className="grid gap-2">
                {detail.items.map((it) => (
                  <div
                    key={it.id}
                    className="rounded-lg border border-border p-3"
                  >
                    <div className="flex flex-wrap items-center gap-2 text-xs">
                      <Badge tone="brand">
                        {CHANNEL_LABELS[it.channel] ?? it.channel}
                      </Badge>
                      <span className="text-muted">
                        🗓 {new Date(it.scheduled_at).toLocaleString()}
                      </span>
                      {it.account_name ? (
                        <span className="text-muted">→ {it.account_name}</span>
                      ) : (
                        <span className="text-amber-600">no connected account</span>
                      )}
                      <span className="ml-auto" />
                      {it.content_item_id && (
                        <button
                          onClick={() => setEditing(it)}
                          className="font-medium text-brand hover:underline"
                        >
                          ✎ Edit
                        </button>
                      )}
                      {it.status !== "proposed" && (
                        <Badge
                          tone={it.status === "scheduled" ? "green" : "default"}
                        >
                          {it.status}
                        </Badge>
                      )}
                    </div>
                    <p className="mt-2 whitespace-pre-wrap text-sm text-fg/90">
                      {it.body}
                    </p>
                  </div>
                ))}
              </div>

              {status === "proposed" && (
                <div className="flex justify-end gap-2">
                  <Button
                    variant="danger"
                    loading={busy === "reject"}
                    onClick={() => act("reject")}
                  >
                    Reject
                  </Button>
                  <Button
                    loading={busy === "approve"}
                    onClick={() => act("approve")}
                  >
                    Approve &amp; schedule
                  </Button>
                </div>
              )}
              {status === "scheduled" && (
                <p className="text-right text-xs text-green-600 dark:text-green-500">
                  Scheduled — the publish engine will post these when due.
                </p>
              )}
            </>
          )}
        </div>
      )}

      {editing?.content_item_id && (
        <PostEditModal
          businessId={businessId}
          post={{
            id: editing.content_item_id,
            title: editing.title,
            body: editing.body ?? "",
            channel: editing.channel,
          }}
          onClose={() => setEditing(null)}
          onSaved={onPostSaved}
        />
      )}
    </Card>
  );
}

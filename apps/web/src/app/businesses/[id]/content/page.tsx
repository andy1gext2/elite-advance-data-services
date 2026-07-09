"use client";

import { use, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import {
  CHANNELS,
  CHANNEL_LABELS,
  type Business,
  type ContentItem,
} from "@/lib/types";
import { AppShell } from "@/components/AppShell";
import { BusinessTabs } from "@/components/BusinessTabs";
import {
  Alert,
  Badge,
  Button,
  Card,
  Field,
  Input,
  Textarea,
} from "@/components/ui";

const STATUS_TONE: Record<string, "green" | "red" | "amber" | "default"> = {
  approved: "green",
  rejected: "red",
  draft: "amber",
};

const STATUSES = ["draft", "approved", "rejected"] as const;

export default function ContentPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [business, setBusiness] = useState<Business | null>(null);
  const [items, setItems] = useState<ContentItem[]>([]);
  const [idea, setIdea] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  // Filters (server-side via query params).
  const [statusFilter, setStatusFilter] = useState("");
  const [channelFilter, setChannelFilter] = useState("");

  const loadItems = useCallback(async () => {
    const content = await api.listContent(id, {
      status: statusFilter || undefined,
      channel: channelFilter || undefined,
    });
    setItems(content);
  }, [id, statusFilter, channelFilter]);

  // Business once; items whenever filters change.
  useEffect(() => {
    api.getBusiness(id).then(setBusiness).catch(() => {});
  }, [id]);

  useEffect(() => {
    loadItems().catch((e) =>
      setError(e instanceof ApiError ? e.message : "Failed to load")
    );
  }, [loadItems]);

  async function onRepurpose(e: React.FormEvent) {
    e.preventDefault();
    if (!idea.trim()) return;
    setError("");
    setBusy(true);
    try {
      await api.repurpose(id, idea.trim());
      setIdea("");
      // Show the fresh drafts regardless of any active filter.
      setStatusFilter("");
      setChannelFilter("");
      await loadItems();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Generation failed");
    } finally {
      setBusy(false);
    }
  }

  function replaceItem(updated: ContentItem) {
    setItems((list) =>
      // Drop it if it no longer matches the active status filter.
      list
        .map((it) => (it.id === updated.id ? updated : it))
        .filter((it) => !statusFilter || it.status === statusFilter)
    );
  }

  async function decide(item: ContentItem, approve: boolean) {
    const prev = items;
    try {
      const updated = approve
        ? await api.approve(id, item.id)
        : await api.reject(id, item.id);
      replaceItem(updated);
    } catch (err) {
      setItems(prev);
      setError(err instanceof ApiError ? err.message : "Update failed");
    }
  }

  return (
    <AppShell>
      <div className="mb-6 flex items-center gap-2 text-sm text-muted">
        <Link href="/dashboard" className="hover:text-fg">
          Dashboard
        </Link>
        <span>/</span>
        <span className="text-fg">{business?.name ?? "…"}</span>
      </div>

      <BusinessTabs businessId={id} />

      <h1 className="mt-6 text-2xl font-semibold">Content studio</h1>
      <p className="mt-1 text-sm text-muted">
        Describe one idea. The AI repurposes it into platform-tailored posts you
        can edit, then approve or reject.
      </p>

      <Card className="mt-6">
        <form onSubmit={onRepurpose} className="space-y-4">
          <Field label="Your idea">
            <Textarea
              rows={3}
              value={idea}
              onChange={(e) => setIdea(e.target.value)}
              placeholder="We're launching a fall pumpkin spice cold brew this week — limited time only."
            />
          </Field>
          <Alert>{error}</Alert>
          <div className="flex justify-end">
            <Button type="submit" loading={busy} disabled={!idea.trim()}>
              {busy ? "Generating…" : "Generate post set"}
            </Button>
          </div>
        </form>
      </Card>

      {/* Library header + filters */}
      <div className="mt-8 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold">
          Content library <span className="text-muted">({items.length})</span>
        </h2>
        <div className="flex flex-wrap gap-2">
          <Select
            value={statusFilter}
            onChange={setStatusFilter}
            allLabel="All statuses"
            options={STATUSES.map((s) => ({ value: s, label: s }))}
          />
          <Select
            value={channelFilter}
            onChange={setChannelFilter}
            allLabel="All channels"
            options={CHANNELS.map((c) => ({
              value: c,
              label: CHANNEL_LABELS[c] ?? c,
            }))}
          />
        </div>
      </div>

      {items.length === 0 ? (
        <p className="mt-4 text-sm text-muted">
          {statusFilter || channelFilter
            ? "No content matches these filters."
            : "Nothing yet — generate your first post set above."}
        </p>
      ) : (
        <div className="mt-4 grid gap-4">
          {items.map((item) => (
            <ContentCard
              key={item.id}
              item={item}
              onDecide={decide}
              onSaved={replaceItem}
              onError={setError}
              businessId={id}
            />
          ))}
        </div>
      )}
    </AppShell>
  );
}

function Select({
  value,
  onChange,
  allLabel,
  options,
}: {
  value: string;
  onChange: (v: string) => void;
  allLabel: string;
  options: { value: string; label: string }[];
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="rounded-lg border border-border bg-bg px-3 py-2 text-sm capitalize text-fg outline-none focus:border-brand focus:ring-2 focus:ring-brand/30"
    >
      <option value="">{allLabel}</option>
      {options.map((o) => (
        <option key={o.value} value={o.value} className="capitalize">
          {o.label}
        </option>
      ))}
    </select>
  );
}

function ContentCard({
  item,
  businessId,
  onDecide,
  onSaved,
  onError,
}: {
  item: ContentItem;
  businessId: string;
  onDecide: (item: ContentItem, approve: boolean) => void;
  onSaved: (updated: ContentItem) => void;
  onError: (msg: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(item.title ?? "");
  const [body, setBody] = useState(item.body);
  const [saving, setSaving] = useState(false);

  function startEdit() {
    setTitle(item.title ?? "");
    setBody(item.body);
    setEditing(true);
  }

  async function save() {
    if (!body.trim()) return;
    setSaving(true);
    try {
      const updated = await api.updateContent(businessId, item.id, {
        title: title.trim() || null,
        body,
      });
      onSaved(updated);
      setEditing(false);
    } catch (err) {
      onError(err instanceof ApiError ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone="brand">
          {CHANNEL_LABELS[item.channel] ?? item.channel}
        </Badge>
        <Badge>{item.content_type.replace(/_/g, " ")}</Badge>
        <span className="ml-auto" />
        <Badge tone={STATUS_TONE[item.status] ?? "default"}>
          {item.status}
        </Badge>
      </div>

      {editing ? (
        <div className="space-y-3">
          <Field label="Title">
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Optional"
            />
          </Field>
          <Field label="Body">
            <Textarea
              rows={5}
              value={body}
              onChange={(e) => setBody(e.target.value)}
            />
          </Field>
          <p className="text-xs text-muted">
            Editing an approved or rejected post sends it back to draft for
            re-review.
          </p>
          <div className="flex justify-end gap-2 border-t border-border pt-3">
            <Button
              variant="ghost"
              onClick={() => setEditing(false)}
              disabled={saving}
            >
              Cancel
            </Button>
            <Button onClick={save} loading={saving} disabled={!body.trim()}>
              Save changes
            </Button>
          </div>
        </div>
      ) : (
        <>
          {item.title && <p className="font-medium">{item.title}</p>}
          <p className="whitespace-pre-wrap text-sm text-fg/90">{item.body}</p>
          <div className="flex justify-end gap-2 border-t border-border pt-3">
            <Button variant="secondary" onClick={startEdit}>
              Edit
            </Button>
            <Button
              variant="danger"
              onClick={() => onDecide(item, false)}
              disabled={item.status === "rejected"}
            >
              Reject
            </Button>
            <Button
              onClick={() => onDecide(item, true)}
              disabled={item.status === "approved"}
            >
              Approve
            </Button>
          </div>
        </>
      )}
    </Card>
  );
}

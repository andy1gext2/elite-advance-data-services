"use client";

import { use, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import {
  CHANNEL_LABELS,
  PLATFORMS,
  PLATFORM_LABELS,
  type Business,
  type ContentItem,
  type RunDueResult,
  type Schedule,
  type SocialAccount,
} from "@/lib/types";
import { AppShell } from "@/components/AppShell";
import { BusinessTabs } from "@/components/BusinessTabs";
import { Alert, Badge, Button, Card, Field, Input } from "@/components/ui";

const STATUS_TONE: Record<string, "green" | "red" | "amber" | "brand" | "default"> = {
  published: "green",
  failed: "red",
  pending: "amber",
  publishing: "brand",
  canceled: "default",
};

function nowLocalInput() {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(
    d.getHours()
  )}:${pad(d.getMinutes())}`;
}

function snippet(item: ContentItem | undefined) {
  if (!item) return "(deleted content)";
  const text = item.title || item.body;
  return text.length > 60 ? text.slice(0, 60) + "…" : text;
}

export default function SchedulePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [business, setBusiness] = useState<Business | null>(null);
  const [accounts, setAccounts] = useState<SocialAccount[]>([]);
  const [items, setItems] = useState<ContentItem[]>([]);
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [runResult, setRunResult] = useState<RunDueResult | null>(null);

  const itemsById = useMemo(
    () => new Map(items.map((i) => [i.id, i])),
    [items]
  );
  const accountsById = useMemo(
    () => new Map(accounts.map((a) => [a.id, a])),
    [accounts]
  );

  const loadSchedules = useCallback(async () => {
    setSchedules(await api.listSchedules(id));
  }, [id]);

  const loadAll = useCallback(async () => {
    const [biz, accs, content, scheds] = await Promise.all([
      api.getBusiness(id),
      api.listAccounts(id),
      api.listContent(id),
      api.listSchedules(id),
    ]);
    setBusiness(biz);
    setAccounts(accs);
    setItems(content);
    setSchedules(scheds);
  }, [id]);

  useEffect(() => {
    loadAll().catch((e) =>
      setError(e instanceof ApiError ? e.message : "Failed to load")
    );
  }, [loadAll]);

  // Surface the OAuth callback result (?connected / ?oauth_error) then clean the URL.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const connected = params.get("connected");
    const oauthError = params.get("oauth_error");
    if (connected) setNotice(`Connected your ${connected.replace(/_/g, " ")} account.`);
    else if (oauthError) setError(`Could not connect account: ${oauthError.replace(/_/g, " ")}`);
    if (connected || oauthError) {
      window.history.replaceState({}, "", window.location.pathname);
    }
  }, []);

  async function onCancel(schedule: Schedule) {
    try {
      const updated = await api.cancelSchedule(id, schedule.id);
      setSchedules((list) =>
        list.map((s) => (s.id === updated.id ? updated : s))
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Cancel failed");
    }
  }

  async function onRunDue() {
    setError("");
    setRunResult(null);
    try {
      setRunResult(await api.runDue(id));
      await loadSchedules();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Publish run failed");
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

      <h1 className="mt-6 text-2xl font-semibold">Scheduling & publishing</h1>
      <p className="mt-1 text-sm text-muted">
        Connect accounts, schedule approved content, and run the publish engine.
      </p>

      <Alert>{error}</Alert>
      {notice && (
        <div className="mt-4 rounded-lg border border-green-500/30 bg-green-500/10 px-3 py-2 text-sm text-green-600 dark:text-green-500">
          {notice}
        </div>
      )}

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <ConnectAccounts businessId={id} accounts={accounts} onError={setError} />
        <ScheduleForm
          businessId={id}
          items={items}
          accounts={accounts}
          onScheduled={(s) => setSchedules((list) => [...list, s])}
          onError={setError}
        />
      </div>

      {/* Schedule list + publish engine */}
      <div className="mt-8 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold">
          Scheduled posts <span className="text-muted">({schedules.length})</span>
        </h2>
        <div className="flex items-center gap-3">
          {runResult && (
            <span className="text-sm text-muted">
              Ran: {runResult.due} due · {runResult.published} published ·{" "}
              {runResult.failed} failed
            </span>
          )}
          <Button variant="secondary" onClick={onRunDue}>
            ▶ Run publish engine
          </Button>
        </div>
      </div>
      <p className="mt-1 text-xs text-muted">
        The engine publishes any schedule whose time has arrived (via the mock
        connector). In production this runs automatically on a Celery beat.
      </p>

      {schedules.length === 0 ? (
        <p className="mt-4 text-sm text-muted">
          No schedules yet. Schedule an approved post above.
        </p>
      ) : (
        <div className="mt-4 grid gap-3">
          {schedules.map((s) => {
            const item = itemsById.get(s.content_item_id);
            const account = accountsById.get(s.social_account_id);
            return (
              <Card key={s.id} className="flex items-start gap-4 p-4">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone="brand">
                      {account
                        ? PLATFORM_LABELS[account.platform] ?? account.platform
                        : "—"}
                    </Badge>
                    {account && (
                      <span className="text-xs text-muted">
                        {account.display_name}
                      </span>
                    )}
                    <span className="ml-auto" />
                    <Badge tone={STATUS_TONE[s.status] ?? "default"}>
                      {s.status}
                    </Badge>
                  </div>
                  <p className="mt-2 truncate text-sm text-fg/90">
                    {snippet(item)}
                  </p>
                  <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
                    <span>🗓 {new Date(s.scheduled_at).toLocaleString()}</span>
                    {s.repost_interval_days && (
                      <span>🔁 every {s.repost_interval_days}d</span>
                    )}
                    {s.attempts > 0 && <span>attempts: {s.attempts}</span>}
                  </div>
                </div>
                {s.status === "pending" && (
                  <Button variant="danger" onClick={() => onCancel(s)}>
                    Cancel
                  </Button>
                )}
              </Card>
            );
          })}
        </div>
      )}
    </AppShell>
  );
}

function ConnectAccounts({
  businessId,
  accounts,
  onError,
}: {
  businessId: string;
  accounts: SocialAccount[];
  onError: (msg: string) => void;
}) {
  const [platform, setPlatform] = useState<string>(PLATFORMS[0]);
  const [busy, setBusy] = useState(false);

  async function connect(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      // Hand off to the provider's consent screen; the callback brings the
      // browser back to this page with ?connected=<platform>.
      const { authorize_url } = await api.startOAuth(businessId, platform);
      window.location.href = authorize_url;
    } catch (err) {
      onError(err instanceof ApiError ? err.message : "Could not start OAuth");
      setBusy(false);
    }
  }

  return (
    <Card>
      <h2 className="font-semibold">Connected accounts</h2>
      <p className="mt-1 text-xs text-muted">
        Connect via OAuth — you&apos;ll approve access on the platform, then land
        back here. (Live connectors await platform API approval; today a mock
        consent screen completes the flow.)
      </p>

      {accounts.length > 0 && (
        <ul className="mt-4 space-y-2">
          {accounts.map((a) => (
            <li
              key={a.id}
              className="flex items-center gap-2 rounded-lg border border-border bg-bg px-3 py-2"
            >
              <Badge tone="brand">
                {PLATFORM_LABELS[a.platform] ?? a.platform}
              </Badge>
              <span className="text-sm">{a.display_name}</span>
              <span className="ml-auto">
                <Badge tone="green">{a.status}</Badge>
              </span>
            </li>
          ))}
        </ul>
      )}

      <form onSubmit={connect} className="mt-4 space-y-3">
        <Field label="Platform">
          <select
            value={platform}
            onChange={(e) => setPlatform(e.target.value)}
            className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-fg outline-none focus:border-brand focus:ring-2 focus:ring-brand/30"
          >
            {PLATFORMS.map((p) => (
              <option key={p} value={p}>
                {PLATFORM_LABELS[p] ?? p}
              </option>
            ))}
          </select>
        </Field>
        <div className="flex justify-end">
          <Button type="submit" loading={busy}>
            Connect with {PLATFORM_LABELS[platform] ?? platform}
          </Button>
        </div>
      </form>
    </Card>
  );
}

function ScheduleForm({
  businessId,
  items,
  accounts,
  onScheduled,
  onError,
}: {
  businessId: string;
  items: ContentItem[];
  accounts: SocialAccount[];
  onScheduled: (s: Schedule) => void;
  onError: (msg: string) => void;
}) {
  const [contentId, setContentId] = useState("");
  const [accountId, setAccountId] = useState("");
  const [when, setWhen] = useState(nowLocalInput());
  const [repost, setRepost] = useState("");
  const [busy, setBusy] = useState(false);

  // Approved content first — that's the intended thing to schedule.
  const sortedItems = useMemo(
    () =>
      [...items].sort((a, b) =>
        a.status === "approved" && b.status !== "approved" ? -1 : 1
      ),
    [items]
  );

  const ready = contentId && accountId && when;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!ready) return;
    setBusy(true);
    try {
      const schedule = await api.createSchedule(businessId, {
        content_item_id: contentId,
        social_account_id: accountId,
        // Convert local input to a tz-aware ISO string so the backend stores UTC correctly.
        scheduled_at: new Date(when).toISOString(),
        repost_interval_days: repost ? Number(repost) : null,
      });
      onScheduled(schedule);
      setContentId("");
    } catch (err) {
      onError(err instanceof ApiError ? err.message : "Schedule failed");
    } finally {
      setBusy(false);
    }
  }

  const selectCls =
    "w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-fg outline-none focus:border-brand focus:ring-2 focus:ring-brand/30";

  return (
    <Card>
      <h2 className="font-semibold">Schedule a post</h2>
      {accounts.length === 0 ? (
        <p className="mt-3 text-sm text-muted">
          Connect an account first, then schedule content to it.
        </p>
      ) : items.length === 0 ? (
        <p className="mt-3 text-sm text-muted">
          No content yet — generate and approve a post in the Content tab.
        </p>
      ) : (
        <form onSubmit={submit} className="mt-4 space-y-3">
          <Field label="Content">
            <select
              value={contentId}
              onChange={(e) => setContentId(e.target.value)}
              className={selectCls}
              required
            >
              <option value="">Select a post…</option>
              {sortedItems.map((i) => (
                <option key={i.id} value={i.id}>
                  [{i.status}] {CHANNEL_LABELS[i.channel] ?? i.channel} —{" "}
                  {snippet(i)}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Account">
            <select
              value={accountId}
              onChange={(e) => setAccountId(e.target.value)}
              className={selectCls}
              required
            >
              <option value="">Select an account…</option>
              {accounts.map((a) => (
                <option key={a.id} value={a.id}>
                  {PLATFORM_LABELS[a.platform] ?? a.platform} · {a.display_name}
                </option>
              ))}
            </select>
          </Field>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="When">
              <Input
                type="datetime-local"
                value={when}
                onChange={(e) => setWhen(e.target.value)}
                required
              />
            </Field>
            <Field label="Repost every (days)" hint="Optional">
              <Input
                type="number"
                min={1}
                value={repost}
                onChange={(e) => setRepost(e.target.value)}
                placeholder="—"
              />
            </Field>
          </div>
          <div className="flex justify-end">
            <Button type="submit" loading={busy} disabled={!ready}>
              Schedule post
            </Button>
          </div>
        </form>
      )}
    </Card>
  );
}

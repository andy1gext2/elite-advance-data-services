"use client";

import { use, useCallback, useEffect, useMemo, useState } from "react";
import { api, ApiError } from "@/lib/api";
import {
  CHANNEL_LABELS,
  PLATFORMS,
  PLATFORM_LABELS,
  type ContentItem,
  type RunDueResult,
  type Schedule,
  type SocialAccount,
} from "@/lib/types";
import { Alert, Badge, Button, Card, Field, Input, PageHeader } from "@/components/ui";

const STATUS_TONE: Record<string, "green" | "red" | "amber" | "brand" | "default"> = {
  published: "green",
  failed: "red",
  pending: "amber",
  publishing: "brand",
  canceled: "default",
};

// Connection-health badge styling for connected accounts.
const CONN_TONE: Record<string, "green" | "amber" | "red" | "default"> = {
  connected: "green",
  expiring_soon: "amber",
  needs_reauth: "red",
  pending_approval: "default",
};
const CONN_LABEL: Record<string, string> = {
  connected: "Connected",
  expiring_soon: "Expiring soon",
  needs_reauth: "Reconnect needed",
  pending_approval: "Pending approval",
};

const pad = (n: number) => String(n).padStart(2, "0");

function nowLocalInput() {
  const d = new Date();
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(
    d.getHours()
  )}:${pad(d.getMinutes())}`;
}

// Backend stores naive UTC; parse it as UTC so display/edit show true local time.
function utcDate(iso: string) {
  return new Date(/[Z+]/.test(iso) ? iso : iso + "Z");
}

function utcToLocalInput(iso: string) {
  const d = utcDate(iso);
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
    const [accs, content, scheds] = await Promise.all([
      api.listAccounts(id),
      api.listContent(id),
      api.listSchedules(id),
    ]);
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
    <>
      <PageHeader
        title="Scheduling & publishing"
        subtitle="Connect accounts, schedule approved content, and run the publish engine."
      />

      <div className="mt-4">
        <Alert>{error}</Alert>
      </div>
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
          {schedules.map((s) => (
            <ScheduledPostCard
              key={s.id}
              businessId={id}
              schedule={s}
              item={itemsById.get(s.content_item_id)}
              account={accountsById.get(s.social_account_id)}
              accounts={accounts}
              onUpdated={(u) =>
                setSchedules((list) => list.map((x) => (x.id === u.id ? u : x)))
              }
              onCancel={onCancel}
              onError={setError}
            />
          ))}
        </div>
      )}
    </>
  );
}

function ScheduledPostCard({
  businessId,
  schedule: s,
  item,
  account,
  accounts,
  onUpdated,
  onCancel,
  onError,
}: {
  businessId: string;
  schedule: Schedule;
  item: ContentItem | undefined;
  account: SocialAccount | undefined;
  accounts: SocialAccount[];
  onUpdated: (s: Schedule) => void;
  onCancel: (s: Schedule) => void;
  onError: (msg: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [when, setWhen] = useState(() => utcToLocalInput(s.scheduled_at));
  const [accountId, setAccountId] = useState(s.social_account_id);
  const [busy, setBusy] = useState(false);

  async function save() {
    setBusy(true);
    try {
      const patch: { scheduled_at?: string; social_account_id?: string } = {
        scheduled_at: new Date(when).toISOString(),
      };
      if (accountId !== s.social_account_id) patch.social_account_id = accountId;
      onUpdated(await api.rescheduleSchedule(businessId, s.id, patch));
      setEditing(false);
    } catch (err) {
      onError(err instanceof ApiError ? err.message : "Reschedule failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card className="p-4">
      <div className="flex items-start gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone="brand">
              {account ? PLATFORM_LABELS[account.platform] ?? account.platform : "—"}
            </Badge>
            {account && <span className="text-xs text-muted">{account.display_name}</span>}
            <span className="ml-auto" />
            <Badge tone={STATUS_TONE[s.status] ?? "default"}>{s.status}</Badge>
          </div>
          <p className="mt-2 truncate text-sm text-fg/90">{snippet(item)}</p>
          <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
            <span>🗓 {utcDate(s.scheduled_at).toLocaleString()}</span>
            {s.repost_interval_days && <span>🔁 every {s.repost_interval_days}d</span>}
            {s.attempts > 0 && <span>attempts: {s.attempts}</span>}
          </div>
        </div>
        {s.status === "pending" && (
          <div className="flex shrink-0 flex-col gap-2">
            <Button variant="secondary" onClick={() => setEditing((v) => !v)}>
              {editing ? "Close" : "Reschedule"}
            </Button>
            <Button variant="danger" onClick={() => onCancel(s)}>
              Cancel
            </Button>
          </div>
        )}
      </div>

      {editing && s.status === "pending" && (
        <div className="mt-3 grid gap-3 border-t border-border pt-3 sm:grid-cols-[1fr_1fr_auto] sm:items-end">
          <Field label="When">
            <Input
              type="datetime-local"
              value={when}
              onChange={(e) => setWhen(e.target.value)}
            />
          </Field>
          <Field label="Account">
            <select
              value={accountId}
              onChange={(e) => setAccountId(e.target.value)}
              className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-fg outline-none focus:border-brand focus:ring-2 focus:ring-brand/30"
            >
              {accounts.map((a) => (
                <option key={a.id} value={a.id}>
                  {PLATFORM_LABELS[a.platform] ?? a.platform} · {a.display_name}
                </option>
              ))}
            </select>
          </Field>
          <Button onClick={save} loading={busy}>
            Save
          </Button>
        </div>
      )}
    </Card>
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

  async function reconnect(p: string) {
    try {
      const { authorize_url } = await api.startOAuth(businessId, p);
      window.location.href = authorize_url;
    } catch (err) {
      onError(err instanceof ApiError ? err.message : "Could not reconnect");
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
              className="flex items-center gap-3 rounded-lg border border-border bg-bg px-3 py-2"
            >
              <Badge tone="brand">
                {PLATFORM_LABELS[a.platform] ?? a.platform}
              </Badge>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm">{a.display_name}</p>
                <p className="truncate text-xs text-muted">{a.detail}</p>
              </div>
              {(a.connection === "needs_reauth" || a.connection === "expiring_soon") && (
                <button
                  onClick={() => reconnect(a.platform)}
                  className="shrink-0 text-xs font-medium text-brand hover:underline"
                >
                  Reconnect
                </button>
              )}
              <Badge tone={CONN_TONE[a.connection] ?? "default"}>
                {CONN_LABEL[a.connection] ?? a.connection}
              </Badge>
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

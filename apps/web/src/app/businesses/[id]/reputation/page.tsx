"use client";

import { use, useCallback, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import {
  PLATFORM_LABELS,
  type ReputationReport,
  type Review,
} from "@/lib/types";
import {
  Alert,
  Badge,
  Button,
  Card,
  PageHeader,
  Textarea,
} from "@/components/ui";

const SENTIMENT_TONE: Record<string, "green" | "red" | "amber" | "default"> = {
  positive: "green",
  negative: "red",
  neutral: "default",
};

function Stars({ n }: { n: number }) {
  return (
    <span className="text-amber-500" aria-label={`${n} out of 5 stars`}>
      {"★".repeat(n)}
      <span className="text-muted">{"★".repeat(5 - n)}</span>
    </span>
  );
}

export default function ReputationPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [report, setReport] = useState<ReputationReport | null>(null);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [error, setError] = useState("");
  const [syncing, setSyncing] = useState(false);

  const [statusFilter, setStatusFilter] = useState("");
  const [sentimentFilter, setSentimentFilter] = useState("");
  const [attentionOnly, setAttentionOnly] = useState(false);

  const loadReviews = useCallback(async () => {
    setReviews(
      await api.listReviews(id, {
        status: statusFilter || undefined,
        sentiment: sentimentFilter || undefined,
        needs_attention: attentionOnly || undefined,
      })
    );
  }, [id, statusFilter, sentimentFilter, attentionOnly]);

  const loadReport = useCallback(async () => {
    setReport(await api.reputationReport(id));
  }, [id]);

  useEffect(() => {
    loadReport().catch(() => {});
  }, [loadReport]);

  useEffect(() => {
    loadReviews().catch((e) =>
      setError(e instanceof ApiError ? e.message : "Failed to load")
    );
  }, [loadReviews]);

  async function onSync() {
    setError("");
    setSyncing(true);
    try {
      await api.syncReviews(id);
      await Promise.all([loadReviews(), loadReport()]);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Sync failed");
    } finally {
      setSyncing(false);
    }
  }

  function onReviewChanged(updated: Review) {
    setReviews((list) => list.map((r) => (r.id === updated.id ? updated : r)));
    loadReport().catch(() => {});
  }

  return (
    <>
      <PageHeader
        title="Reputation"
        subtitle="Monitor reviews, gauge sentiment, and reply with AI."
        action={
          <Button onClick={onSync} loading={syncing}>
            {syncing ? "Syncing…" : "⟳ Sync reviews"}
          </Button>
        }
      />

      <div className="mt-4">
        <Alert>{error}</Alert>
      </div>

      {report && <ReportSummary report={report} />}

      {/* Filters */}
      <div className="mt-8 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold">
          Reviews <span className="text-muted">({reviews.length})</span>
        </h2>
        <div className="flex flex-wrap items-center gap-2">
          <FilterSelect
            value={statusFilter}
            onChange={setStatusFilter}
            allLabel="All statuses"
            options={[
              { value: "new", label: "New" },
              { value: "responded", label: "Responded" },
            ]}
          />
          <FilterSelect
            value={sentimentFilter}
            onChange={setSentimentFilter}
            allLabel="All sentiment"
            options={[
              { value: "positive", label: "Positive" },
              { value: "neutral", label: "Neutral" },
              { value: "negative", label: "Negative" },
            ]}
          />
          <label className="flex cursor-pointer items-center gap-2 rounded-lg border border-border px-3 py-2 text-sm">
            <input
              type="checkbox"
              checked={attentionOnly}
              onChange={(e) => setAttentionOnly(e.target.checked)}
            />
            Needs attention
          </label>
        </div>
      </div>

      {reviews.length === 0 ? (
        <p className="mt-4 text-sm text-muted">
          No reviews yet — click <strong>Sync reviews</strong> to pull them in.
        </p>
      ) : (
        <div className="mt-4 grid gap-4">
          {reviews.map((rv) => (
            <ReviewCard
              key={rv.id}
              businessId={id}
              review={rv}
              onChanged={onReviewChanged}
              onError={setError}
            />
          ))}
        </div>
      )}
    </>
  );
}

function ReportSummary({ report }: { report: ReputationReport }) {
  const s = report.sentiment;
  const totalSent = (s.positive || 0) + (s.neutral || 0) + (s.negative || 0) || 1;
  const trendDelta = report.reviews_this_month - report.reviews_last_month;

  return (
    <div className="mt-6 grid gap-4 md:grid-cols-4">
      <Card>
        <p className="text-xs uppercase tracking-wide text-muted">Avg rating</p>
        <p className="mt-1 text-2xl font-semibold">
          {report.average_rating.toFixed(1)}
        </p>
        <Stars n={Math.round(report.average_rating)} />
      </Card>
      <Card>
        <p className="text-xs uppercase tracking-wide text-muted">Total reviews</p>
        <p className="mt-1 text-2xl font-semibold">{report.total_reviews}</p>
        <p className="text-xs text-muted">
          {report.reviews_this_month} this month
          {trendDelta !== 0 && (
            <span className={trendDelta > 0 ? "text-green-500" : "text-red-500"}>
              {" "}
              ({trendDelta > 0 ? "+" : ""}
              {trendDelta} vs last)
            </span>
          )}
        </p>
      </Card>
      <Card>
        <p className="text-xs uppercase tracking-wide text-muted">Response rate</p>
        <p className="mt-1 text-2xl font-semibold">
          {Math.round(report.response_rate * 100)}%
        </p>
      </Card>
      <Card>
        <p className="text-xs uppercase tracking-wide text-muted">Needs attention</p>
        <p
          className={
            "mt-1 text-2xl font-semibold " +
            (report.needs_attention > 0 ? "text-red-500" : "")
          }
        >
          {report.needs_attention}
        </p>
      </Card>

      {/* Sentiment bar */}
      <Card className="md:col-span-2">
        <p className="text-xs uppercase tracking-wide text-muted">Sentiment</p>
        <div className="mt-3 flex h-3 overflow-hidden rounded-full">
          <div
            className="bg-green-500"
            style={{ width: `${((s.positive || 0) / totalSent) * 100}%` }}
          />
          <div
            className="bg-zinc-400"
            style={{ width: `${((s.neutral || 0) / totalSent) * 100}%` }}
          />
          <div
            className="bg-red-500"
            style={{ width: `${((s.negative || 0) / totalSent) * 100}%` }}
          />
        </div>
        <div className="mt-2 flex gap-4 text-xs text-muted">
          <span>😊 {s.positive || 0} positive</span>
          <span>😐 {s.neutral || 0} neutral</span>
          <span>☹️ {s.negative || 0} negative</span>
        </div>
      </Card>

      {/* Compliments / complaints */}
      <Card>
        <p className="text-xs uppercase tracking-wide text-muted">Top compliments</p>
        <KeywordChips items={report.top_compliments} tone="green" />
      </Card>
      <Card>
        <p className="text-xs uppercase tracking-wide text-muted">Top complaints</p>
        <KeywordChips items={report.top_complaints} tone="red" />
      </Card>
    </div>
  );
}

function KeywordChips({
  items,
  tone,
}: {
  items: { keyword: string; count: number }[];
  tone: "green" | "red";
}) {
  if (items.length === 0)
    return <p className="mt-2 text-sm text-muted">—</p>;
  return (
    <div className="mt-2 flex flex-wrap gap-1.5">
      {items.map((k) => (
        <Badge key={k.keyword} tone={tone}>
          {k.keyword} · {k.count}
        </Badge>
      ))}
    </div>
  );
}

function ReviewCard({
  businessId,
  review,
  onChanged,
  onError,
}: {
  businessId: string;
  review: Review;
  onChanged: (r: Review) => void;
  onError: (msg: string) => void;
}) {
  const [draft, setDraft] = useState(review.response_text ?? "");
  const [busy, setBusy] = useState<"gen" | "save" | "post" | null>(null);
  const responded = review.status === "responded";

  async function run(kind: "gen" | "save" | "post", fn: () => Promise<Review>) {
    setBusy(kind);
    try {
      const updated = await fn();
      setDraft(updated.response_text ?? "");
      onChanged(updated);
    } catch (err) {
      onError(err instanceof ApiError ? err.message : "Action failed");
    } finally {
      setBusy(null);
    }
  }

  return (
    <Card className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <Stars n={review.rating} />
        <span className="text-sm font-medium">
          {review.author_name ?? "Anonymous"}
        </span>
        <span className="text-xs text-muted">
          · {PLATFORM_LABELS[review.platform] ?? review.platform}
        </span>
        <span className="ml-auto" />
        {review.needs_attention && <Badge tone="amber">needs attention</Badge>}
        <Badge tone={SENTIMENT_TONE[review.sentiment] ?? "default"}>
          {review.sentiment}
        </Badge>
        <Badge tone={responded ? "green" : "default"}>{review.status}</Badge>
      </div>

      <p className="whitespace-pre-wrap text-sm text-fg/90">{review.body}</p>

      {review.keywords.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {review.keywords.slice(0, 6).map((k) => (
            <span
              key={k}
              className="rounded-full border border-border px-2 py-0.5 text-xs text-muted"
            >
              {k}
            </span>
          ))}
        </div>
      )}

      {/* Response area */}
      <div className="rounded-lg border border-border bg-bg p-3">
        {responded ? (
          <>
            <p className="mb-1 text-xs font-medium text-green-500">
              Your reply (posted)
            </p>
            <p className="whitespace-pre-wrap text-sm text-fg/90">
              {review.response_text}
            </p>
          </>
        ) : (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <p className="text-xs font-medium text-muted">Reply</p>
              <Button
                variant="ghost"
                loading={busy === "gen"}
                onClick={() =>
                  run("gen", () =>
                    api.generateReviewResponse(businessId, review.id)
                  )
                }
              >
                ✨ {review.response_text ? "Regenerate" : "Generate AI reply"}
              </Button>
            </div>
            <Textarea
              rows={3}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="Write a reply, or generate one with AI…"
            />
            <div className="flex justify-end gap-2">
              <Button
                variant="secondary"
                loading={busy === "save"}
                disabled={!draft.trim()}
                onClick={() =>
                  run("save", () =>
                    api.editReviewResponse(businessId, review.id, draft)
                  )
                }
              >
                Save draft
              </Button>
              <Button
                loading={busy === "post"}
                disabled={!draft.trim()}
                onClick={async () => {
                  // Persist any edits before posting.
                  await run("post", async () => {
                    if (draft !== (review.response_text ?? "")) {
                      await api.editReviewResponse(businessId, review.id, draft);
                    }
                    return api.postReviewResponse(businessId, review.id);
                  });
                }}
              >
                Post reply
              </Button>
            </div>
          </div>
        )}
      </div>
    </Card>
  );
}

function FilterSelect({
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
      className="rounded-lg border border-border bg-bg px-3 py-2 text-sm text-fg outline-none focus:border-brand focus:ring-2 focus:ring-brand/30"
    >
      <option value="">{allLabel}</option>
      {options.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
  );
}

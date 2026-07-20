// Typed client for the FastAPI backend. All requests go to the same Next origin
// under /api/*, which next.config.mjs proxies to the backend (no CORS).

import type {
  AdminUsage,
  Asset,
  AutopilotConfig,
  BillingStatus,
  Business,
  Campaign,
  CampaignCalendarItem,
  CampaignDetail,
  ContentItem,
  Dashboard,
  Insights,
  Me,
  Plan,
  ReputationReport,
  RepurposeResult,
  Review,
  RunDueResult,
  Schedule,
  SocialAccount,
  SubscriptionPlan,
  Timeframe,
  Tokens,
  VideoJob,
  VideoQuota,
} from "./types";

const ACCESS_KEY = "eads.access";
const REFRESH_KEY = "eads.refresh";

export const tokenStore = {
  get access() {
    if (typeof window === "undefined") return null;
    return localStorage.getItem(ACCESS_KEY);
  },
  get refresh() {
    if (typeof window === "undefined") return null;
    return localStorage.getItem(REFRESH_KEY);
  },
  set(tokens: Tokens) {
    localStorage.setItem(ACCESS_KEY, tokens.access_token);
    localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

type Options = {
  method?: string;
  body?: unknown;
  auth?: boolean;
  // Internal: prevents infinite refresh recursion.
  _retried?: boolean;
};

async function request<T>(path: string, opts: Options = {}): Promise<T> {
  const { method = "GET", body, auth = true } = opts;
  const headers: Record<string, string> = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (auth && tokenStore.access) {
    headers["Authorization"] = `Bearer ${tokenStore.access}`;
  }

  const res = await fetch(path, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  // Transparently refresh once on a 401, then retry the original request.
  if (res.status === 401 && auth && !opts._retried && tokenStore.refresh) {
    const refreshed = await tryRefresh();
    if (refreshed) return request<T>(path, { ...opts, _retried: true });
  }

  if (!res.ok) {
    throw new ApiError(res.status, await errorMessage(res));
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

async function errorMessage(res: Response): Promise<string> {
  try {
    const data = await res.json();
    if (typeof data?.detail === "string") return data.detail;
    if (Array.isArray(data?.detail) && data.detail[0]?.msg) {
      return data.detail[0].msg;
    }
    return JSON.stringify(data);
  } catch {
    return `Request failed (${res.status})`;
  }
}

async function tryRefresh(): Promise<boolean> {
  const refresh_token = tokenStore.refresh;
  if (!refresh_token) return false;
  try {
    const res = await fetch("/api/v1/auth/refresh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token }),
    });
    if (!res.ok) return false;
    tokenStore.set((await res.json()) as Tokens);
    return true;
  } catch {
    return false;
  }
}

export const api = {
  // --- auth ---
  signup: (email: string, password: string, full_name?: string) =>
    request<Tokens>("/api/v1/auth/signup", {
      method: "POST",
      auth: false,
      body: { email, password, full_name: full_name || null },
    }),

  login: (email: string, password: string) =>
    request<Tokens>("/api/v1/auth/login", {
      method: "POST",
      auth: false,
      body: { email, password },
    }),

  me: () => request<Me>("/api/v1/auth/me"),

  forgotPassword: (email: string) =>
    request<{ message: string; dev_code: string | null }>(
      "/api/v1/auth/forgot-password",
      { method: "POST", auth: false, body: { email } }
    ),

  resetPassword: (email: string, code: string, new_password: string) =>
    request<void>("/api/v1/auth/reset-password", {
      method: "POST",
      auth: false,
      body: { email, code, new_password },
    }),

  // --- operator (admin-only) ---
  adminUsage: () => request<AdminUsage>("/api/v1/admin/usage"),

  adminSetPlan: (businessId: string, tier: string) =>
    request<{ business_id: string; tier: string; plan: string }>(
      `/api/v1/admin/businesses/${businessId}/plan`,
      { method: "POST", body: { tier } }
    ),

  // --- businesses ---
  listBusinesses: () => request<Business[]>("/api/v1/businesses"),

  createBusiness: (data: Partial<Business>) =>
    request<Business>("/api/v1/businesses", { method: "POST", body: data }),

  getBusiness: (id: string) => request<Business>(`/api/v1/businesses/${id}`),

  updateBusiness: (id: string, data: Partial<Business>) =>
    request<Business>(`/api/v1/businesses/${id}`, { method: "PATCH", body: data }),

  deleteBusiness: (id: string) =>
    request<void>(`/api/v1/businesses/${id}`, { method: "DELETE" }),

  uploadBusinessLogo: async (id: string, file: File): Promise<Business> => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`/api/v1/businesses/${id}/logo`, {
      method: "POST",
      headers: tokenStore.access
        ? { Authorization: `Bearer ${tokenStore.access}` }
        : {},
      body: form,
    });
    if (!res.ok) throw new ApiError(res.status, await errorMessage(res));
    return (await res.json()) as Business;
  },

  deleteBusinessLogo: (id: string) =>
    request<Business>(`/api/v1/businesses/${id}/logo`, { method: "DELETE" }),

  // --- content ---
  listContent: (businessId: string, filters?: { status?: string; channel?: string }) => {
    const params = new URLSearchParams();
    if (filters?.status) params.set("status", filters.status);
    if (filters?.channel) params.set("channel", filters.channel);
    const q = params.toString() ? `?${params.toString()}` : "";
    return request<ContentItem[]>(
      `/api/v1/businesses/${businessId}/content${q}`
    );
  },

  updateContent: (
    businessId: string,
    itemId: string,
    patch: { title?: string | null; body?: string }
  ) =>
    request<ContentItem>(
      `/api/v1/businesses/${businessId}/content/${itemId}`,
      { method: "PATCH", body: patch }
    ),

  generateImage: (businessId: string, itemId: string, assetId?: string) => {
    const q = assetId ? `?asset_id=${assetId}` : "";
    return request<ContentItem>(
      `/api/v1/businesses/${businessId}/content/${itemId}/image${q}`,
      { method: "POST" }
    );
  },

  // Have Claude write the 8-second vision for this post (preview/edit before rendering).
  generateVideoScript: (businessId: string, itemId: string) =>
    request<{ prompt: string }>(
      `/api/v1/businesses/${businessId}/content/${itemId}/video/script`,
      { method: "POST" }
    ),

  // Kick off an async video render; poll getVideoJob until it succeeds/fails.
  // Pass an edited `prompt` to render that vision verbatim; omit to let Claude write it.
  generateVideo: (businessId: string, itemId: string, prompt?: string) =>
    request<VideoJob>(
      `/api/v1/businesses/${businessId}/content/${itemId}/video`,
      { method: "POST", body: prompt ? { prompt } : undefined }
    ),

  getVideoJob: (businessId: string, itemId: string) =>
    request<VideoJob>(`/api/v1/businesses/${businessId}/content/${itemId}/video`),

  videoQuota: (businessId: string) =>
    request<VideoQuota>(`/api/v1/businesses/${businessId}/content/video-quota`),

  buyVideoCredits: (businessId: string, quantity: number) =>
    request<VideoQuota>(`/api/v1/businesses/${businessId}/content/video-credits`, {
      method: "POST",
      body: { quantity },
    }),

  // --- assets (product images) ---
  listAssets: (businessId: string) =>
    request<Asset[]>(`/api/v1/businesses/${businessId}/assets`),

  uploadAsset: async (
    businessId: string,
    file: File | null,
    meta?: { name?: string; description?: string; kind?: "product" | "service" }
  ): Promise<Asset> => {
    const form = new FormData();
    if (file) form.append("file", file);
    if (meta?.kind) form.append("kind", meta.kind);
    if (meta?.name) form.append("name", meta.name);
    if (meta?.description) form.append("description", meta.description);
    const res = await fetch(`/api/v1/businesses/${businessId}/assets`, {
      method: "POST",
      headers: tokenStore.access
        ? { Authorization: `Bearer ${tokenStore.access}` }
        : {},
      body: form,
    });
    if (!res.ok) throw new ApiError(res.status, await errorMessage(res));
    return (await res.json()) as Asset;
  },

  updateAsset: async (
    businessId: string,
    assetId: string,
    fields: { name?: string; description?: string; file?: File | null }
  ): Promise<Asset> => {
    const form = new FormData();
    if (fields.name !== undefined) form.append("name", fields.name);
    if (fields.description !== undefined) form.append("description", fields.description);
    if (fields.file) form.append("file", fields.file);
    const res = await fetch(`/api/v1/businesses/${businessId}/assets/${assetId}`, {
      method: "PATCH",
      headers: tokenStore.access
        ? { Authorization: `Bearer ${tokenStore.access}` }
        : {},
      body: form,
    });
    if (!res.ok) throw new ApiError(res.status, await errorMessage(res));
    return (await res.json()) as Asset;
  },

  // Generate an AI flyer/poster for a service, stored on the asset itself. That
  // exact image is reused across every post of a campaign promoting the service.
  generateFlyer: (businessId: string, assetId: string) =>
    request<Asset>(`/api/v1/businesses/${businessId}/assets/${assetId}/flyer`, {
      method: "POST",
    }),

  deleteAsset: (businessId: string, assetId: string) =>
    request<void>(`/api/v1/businesses/${businessId}/assets/${assetId}`, {
      method: "DELETE",
    }),

  uploadContentMedia: async (
    businessId: string,
    file: File,
    caption?: string
  ): Promise<ContentItem[]> => {
    const form = new FormData();
    form.append("file", file);
    if (caption) form.append("caption", caption);
    const res = await fetch(`/api/v1/businesses/${businessId}/content/upload`, {
      method: "POST",
      headers: tokenStore.access
        ? { Authorization: `Bearer ${tokenStore.access}` }
        : {},
      body: form,
    });
    if (!res.ok) throw new ApiError(res.status, await errorMessage(res));
    return (await res.json()) as ContentItem[];
  },

  repurpose: (businessId: string, idea: string) =>
    request<RepurposeResult>(
      `/api/v1/businesses/${businessId}/content/repurpose`,
      { method: "POST", body: { idea } }
    ),

  approve: (businessId: string, itemId: string) =>
    request<ContentItem>(
      `/api/v1/businesses/${businessId}/content/${itemId}/approve`,
      { method: "POST" }
    ),

  reject: (businessId: string, itemId: string) =>
    request<ContentItem>(
      `/api/v1/businesses/${businessId}/content/${itemId}/reject`,
      { method: "POST" }
    ),

  deleteContent: (businessId: string, itemId: string) =>
    request<void>(`/api/v1/businesses/${businessId}/content/${itemId}`, {
      method: "DELETE",
    }),

  // --- calendar ---
  planCalendar: (businessId: string, timeframe: Timeframe, theme: string) =>
    request<Plan>(`/api/v1/businesses/${businessId}/calendar/plan`, {
      method: "POST",
      body: { timeframe, theme },
    }),

  scheduleSlot: (
    businessId: string,
    slot: { channel: string; topic: string; scheduled_at: string }
  ) =>
    request<{ content_item: ContentItem; schedule: Schedule }>(
      `/api/v1/businesses/${businessId}/calendar/schedule-slot`,
      { method: "POST", body: { ...slot, content_type: "social_post" } }
    ),

  // --- integrations / accounts ---
  listAccounts: (businessId: string) =>
    request<SocialAccount[]>(
      `/api/v1/businesses/${businessId}/integrations/accounts`
    ),

  connectAccount: (
    businessId: string,
    data: { platform: string; display_name: string; external_id?: string | null }
  ) =>
    request<SocialAccount>(
      `/api/v1/businesses/${businessId}/integrations/accounts`,
      { method: "POST", body: data }
    ),

  // Start the OAuth connect flow — returns the provider consent URL to redirect to.
  startOAuth: (businessId: string, platform: string) =>
    request<{ authorize_url: string }>(
      `/api/v1/businesses/${businessId}/integrations/oauth/${platform}/start`,
      { method: "POST" }
    ),

  // --- schedules ---
  listSchedules: (businessId: string, status?: string) => {
    const q = status ? `?status=${encodeURIComponent(status)}` : "";
    return request<Schedule[]>(
      `/api/v1/businesses/${businessId}/schedules${q}`
    );
  },

  createSchedule: (
    businessId: string,
    data: {
      content_item_id: string;
      social_account_id: string;
      scheduled_at: string;
      repost_interval_days?: number | null;
    }
  ) =>
    request<Schedule>(`/api/v1/businesses/${businessId}/schedules`, {
      method: "POST",
      body: data,
    }),

  rescheduleSchedule: (
    businessId: string,
    scheduleId: string,
    patch: { scheduled_at?: string; social_account_id?: string }
  ) =>
    request<Schedule>(
      `/api/v1/businesses/${businessId}/schedules/${scheduleId}`,
      { method: "PATCH", body: patch }
    ),

  cancelSchedule: (businessId: string, scheduleId: string) =>
    request<Schedule>(
      `/api/v1/businesses/${businessId}/schedules/${scheduleId}/cancel`,
      { method: "POST" }
    ),

  runDue: (businessId: string) =>
    request<RunDueResult>(
      `/api/v1/businesses/${businessId}/schedules/run-due`,
      { method: "POST" }
    ),

  // --- reputation ---
  syncReviews: (businessId: string, platform?: string) =>
    request<{ fetched: number; new: number }>(
      `/api/v1/businesses/${businessId}/reviews/sync`,
      { method: "POST", body: { platform: platform ?? null } }
    ),

  listReviews: (
    businessId: string,
    filters?: { status?: string; sentiment?: string; needs_attention?: boolean }
  ) => {
    const params = new URLSearchParams();
    if (filters?.status) params.set("status", filters.status);
    if (filters?.sentiment) params.set("sentiment", filters.sentiment);
    if (filters?.needs_attention) params.set("needs_attention", "true");
    const q = params.toString() ? `?${params.toString()}` : "";
    return request<Review[]>(`/api/v1/businesses/${businessId}/reviews${q}`);
  },

  generateReviewResponse: (businessId: string, reviewId: string) =>
    request<Review>(
      `/api/v1/businesses/${businessId}/reviews/${reviewId}/respond/generate`,
      { method: "POST" }
    ),

  editReviewResponse: (businessId: string, reviewId: string, response_text: string) =>
    request<Review>(
      `/api/v1/businesses/${businessId}/reviews/${reviewId}/response`,
      { method: "PATCH", body: { response_text } }
    ),

  postReviewResponse: (businessId: string, reviewId: string) =>
    request<Review>(
      `/api/v1/businesses/${businessId}/reviews/${reviewId}/respond`,
      { method: "POST" }
    ),

  reputationReport: (businessId: string) =>
    request<ReputationReport>(
      `/api/v1/businesses/${businessId}/reputation/report`
    ),

  // --- analytics & insights ---
  dashboard: (businessId: string) =>
    request<Dashboard>(`/api/v1/businesses/${businessId}/analytics/dashboard`),

  generateInsights: (businessId: string) =>
    request<Insights>(`/api/v1/businesses/${businessId}/insights/generate`, {
      method: "POST",
    }),

  // --- campaigns & autopilot ---
  listCampaigns: (businessId: string, status?: string) => {
    const q = status ? `?status=${encodeURIComponent(status)}` : "";
    return request<Campaign[]>(`/api/v1/businesses/${businessId}/campaigns${q}`);
  },

  getCampaign: (businessId: string, id: string) =>
    request<CampaignDetail>(`/api/v1/businesses/${businessId}/campaigns/${id}`),

  proposeCampaign: (
    businessId: string,
    theme: string,
    timeframe: Timeframe,
    productAssetId?: string,
    startDate?: string
  ) =>
    request<CampaignDetail>(`/api/v1/businesses/${businessId}/campaigns/propose`, {
      method: "POST",
      body: {
        theme,
        timeframe,
        product_asset_id: productAssetId ?? null,
        start_date: startDate ?? null,
      },
    }),

  campaignCalendar: (businessId: string) =>
    request<CampaignCalendarItem[]>(
      `/api/v1/businesses/${businessId}/campaigns/calendar`
    ),

  approveCampaign: (businessId: string, id: string) =>
    request<CampaignDetail>(
      `/api/v1/businesses/${businessId}/campaigns/${id}/approve`,
      { method: "POST" }
    ),

  rejectCampaign: (businessId: string, id: string) =>
    request<CampaignDetail>(
      `/api/v1/businesses/${businessId}/campaigns/${id}/reject`,
      { method: "POST" }
    ),

  // --- billing ---
  listPlans: () => request<SubscriptionPlan[]>("/api/v1/plans", { auth: false }),

  billingStatus: (businessId: string) =>
    request<BillingStatus>(`/api/v1/businesses/${businessId}/billing/status`),

  billingCheckout: (businessId: string, tier: string) =>
    request<{ url: string | null }>(
      `/api/v1/businesses/${businessId}/billing/checkout`,
      { method: "POST", body: { tier } }
    ),

  billingCreditsCheckout: (businessId: string) =>
    request<{ url: string | null }>(
      `/api/v1/businesses/${businessId}/billing/credits-checkout`,
      { method: "POST" }
    ),

  billingPortal: (businessId: string) =>
    request<{ url: string | null }>(
      `/api/v1/businesses/${businessId}/billing/portal`,
      { method: "POST" }
    ),

  getAutopilot: (businessId: string) =>
    request<AutopilotConfig>(`/api/v1/businesses/${businessId}/autopilot`),

  setAutopilot: (businessId: string, cfg: AutopilotConfig) =>
    request<AutopilotConfig>(`/api/v1/businesses/${businessId}/autopilot`, {
      method: "PUT",
      body: cfg,
    }),
};

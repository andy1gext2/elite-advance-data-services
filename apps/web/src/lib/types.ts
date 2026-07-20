// Mirrors the FastAPI response schemas (services/api/app/schemas/*).

export interface Tokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
}

export interface Membership {
  business_id: string;
  role: string;
}

export interface Me {
  user: User;
  memberships: Membership[];
  is_platform_admin: boolean;
}

// Operator cost dashboard (GET /admin/usage) — cross-tenant, admin-only.
export interface AdminUsageRow {
  business_id: string;
  name: string;
  plan: string | null;
  tier: string | null;
  mrr_usd: number;
  text_generations: number;
  input_tokens: number;
  output_tokens: number;
  text_cost_usd: number;
  images: number;
  image_cost_usd: number;
  videos: number;
  video_cost_usd: number;
  total_cost_usd: number;
  margin_usd: number;
}

export interface AdminUsage {
  period_start: string;
  totals: {
    businesses: number;
    mrr_usd: number;
    total_cost_usd: number;
    margin_usd: number;
  };
  businesses: AdminUsageRow[];
}

export interface Business {
  id: string;
  name: string;
  industry: string | null;
  website: string | null;
  description: string | null;
  target_audience: string | null;
  brand_voice: string | null;
  tone: string | null;
  goals: string | null;
  timezone: string;
  status: string;
  logo_url: string | null;
  plan_id: string | null;
}

export interface ContentItem {
  id: string;
  idea_id: string | null;
  product_asset_id: string | null;
  channel: string;
  content_type: string;
  title: string | null;
  body: string;
  meta: Record<string, unknown>;
  status: string;
  image_url: string | null;
  image_prompt: string | null;
  video_url: string | null;
}

export interface VideoJob {
  id: string;
  content_item_id: string;
  status: "processing" | "succeeded" | "failed";
  video_url: string | null;
  error: string | null;
}

export interface VideoQuota {
  used: number;
  limit: number | null;
  remaining: number | null;
  unlimited: boolean;
  credits: number;
}

export interface ContentIdea {
  id: string;
  brief: string;
  goal: string | null;
}

export interface RepurposeResult {
  idea: ContentIdea;
  items: ContentItem[];
}

export interface SocialAccount {
  id: string;
  platform: string;
  display_name: string;
  external_id: string | null;
  status: string;
  // Live connection health.
  connection: "connected" | "expiring_soon" | "needs_reauth" | "pending_approval";
  can_publish: boolean;
  live: boolean;
  expires_at: string | null;
  detail: string;
}

export interface Schedule {
  id: string;
  content_item_id: string;
  social_account_id: string;
  scheduled_at: string; // ISO datetime
  status: string;
  repost_interval_days: number | null;
  attempts: number;
}

export interface RunDueResult {
  due: number;
  published: number;
  failed: number;
}

// Connectable platforms (app/models/enums.py Platform).
export const PLATFORMS = [
  "instagram",
  "facebook",
  "linkedin",
  "x",
  "threads",
  "google_business",
  "tiktok",
  "youtube",
] as const;

export const PLATFORM_LABELS: Record<string, string> = {
  instagram: "Instagram",
  facebook: "Facebook",
  linkedin: "LinkedIn",
  x: "X",
  threads: "Threads",
  google_business: "Google Business",
  tiktok: "TikTok",
  youtube: "YouTube",
};

export interface Review {
  id: string;
  platform: string;
  external_id: string;
  author_name: string | null;
  rating: number;
  body: string;
  sentiment: string;
  keywords: string[];
  status: string;
  needs_attention: boolean;
  response_text: string | null;
  reviewed_at: string | null;
}

export interface Asset {
  id: string;
  kind: string; // "product" | "service"
  filename: string;
  name: string | null;
  description: string | null;
  content_type: string | null;
  url: string | null; // null for a service with no uploaded photo
  created_at: string;
}

export interface KeywordCount {
  keyword: string;
  count: number;
}

export interface ReputationReport {
  total_reviews: number;
  average_rating: number;
  response_rate: number;
  needs_attention: number;
  rating_distribution: Record<string, number>;
  sentiment: Record<string, number>;
  top_compliments: KeywordCount[];
  top_complaints: KeywordCount[];
  reviews_this_month: number;
  reviews_last_month: number;
}

export interface WeekPoint {
  week: string;
  count: number;
}

export interface Dashboard {
  kpis: {
    total_content: number;
    published_posts: number;
    pending_schedules: number;
    total_reviews: number;
    average_rating: number;
    response_rate: number;
    needs_attention: number;
    ai_generations_total: number;
    ai_generations_this_month: number;
  };
  content_by_status: Record<string, number>;
  content_by_channel: Record<string, number>;
  sentiment: Record<string, number>;
  timeseries: {
    content_per_week: WeekPoint[];
    reviews_per_week: WeekPoint[];
  };
  trends: {
    content_this_month: number;
    content_last_month: number;
    reviews_this_month: number;
    reviews_last_month: number;
  };
  recommendations: string[];
}

export interface Insights {
  summary: string;
  recommendations: string[];
}

export interface SubscriptionPlan {
  tier: string;
  name: string;
  /** Advertised price in USD cents/month (e.g. 5999 = $59.99; 0 = custom). */
  price_monthly: number;
  max_users: number;
  max_social_accounts: number;
  max_locations: number;
  ai_monthly_quota: number;
  image_monthly_quota: number;
  video_monthly_quota: number;
  features: Record<string, boolean>;
}

export interface BillingStatus {
  enabled: boolean;
  plan_tier: string | null;
  plan_name: string | null;
  subscription_status: string | null;
  video_credits: number;
}

export type Timeframe = "day" | "week" | "month" | "quarter" | "year";

// A dated campaign post for the calendar bird's-eye view.
export interface CampaignCalendarItem {
  id: string;
  campaign_id: string;
  campaign_name: string;
  channel: string;
  scheduled_at: string; // ISO datetime
  status: string;
  content_item_id: string | null;
  title: string | null;
  body: string | null;
}

export interface CampaignItem {
  id: string;
  channel: string;
  scheduled_at: string;
  status: string;
  content_item_id: string | null;
  social_account_id: string | null;
  body: string | null;
  title: string | null;
  account_name: string | null;
}

export interface Campaign {
  id: string;
  name: string;
  timeframe: string;
  status: string;
  source: string;
  created_at: string;
}

export interface CampaignDetail extends Campaign {
  items: CampaignItem[];
}

export interface AutopilotConfig {
  autopilot_enabled: boolean;
  autopilot_theme: string | null;
  autopilot_frequency_days: number;
  autopilot_timeframe: string;
  autopilot_last_run_at: string | null;
}

export interface PlanSlot {
  date: string; // YYYY-MM-DD
  channel: string;
  recommended_time: string; // HH:MM
  topic: string;
}

export interface Plan {
  timeframe: string;
  slots: PlanSlot[];
}

// Enum value lists (kept in sync with app/models/enums.py). Ordered by popularity
// so the most-used platforms (Instagram, Facebook, X) surface first in the UI.
export const CHANNELS = [
  "instagram",
  "facebook",
  "x",
  "linkedin",
  "threads",
  "google_business",
  "blog",
  "email",
  "sms",
  "video",
  "generic",
] as const;

// Sort key for ordering posts/channels by popularity (lower = more popular).
export function channelRank(channel: string): number {
  const i = (CHANNELS as readonly string[]).indexOf(channel);
  return i === -1 ? CHANNELS.length : i;
}

export const CHANNEL_LABELS: Record<string, string> = {
  instagram: "Instagram",
  facebook: "Facebook",
  linkedin: "LinkedIn",
  x: "X",
  threads: "Threads",
  google_business: "Google Business",
  blog: "Blog",
  email: "Email",
  sms: "SMS",
  video: "Video",
  generic: "Generic",
};

// Each channel's dominant brand color (from its app icon), used to color charts
// so the "content by channel" wheel reads at a glance. Falls back to the app's
// brand hue for anything unmapped.
export const CHANNEL_COLORS: Record<string, string> = {
  instagram: "#E1306C", // Instagram magenta/pink
  facebook: "#1877F2", // Facebook blue
  linkedin: "#0A66C2", // LinkedIn blue
  x: "#000000", // X black
  threads: "#737373", // Threads (monochrome) — gray, distinct from X
  google_business: "#4285F4", // Google blue
  blog: "#F59E0B", // amber (no brand)
  email: "#EA4335", // red
  sms: "#22C55E", // green
  video: "#8B5CF6", // violet
  generic: "#6B7280", // gray
};

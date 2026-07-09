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
  plan_id: string | null;
}

export interface ContentItem {
  id: string;
  idea_id: string | null;
  channel: string;
  content_type: string;
  title: string | null;
  body: string;
  meta: Record<string, unknown>;
  status: string;
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

export type Timeframe = "week" | "month" | "quarter" | "year";

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

// Enum value lists (kept in sync with app/models/enums.py).
export const CHANNELS = [
  "instagram",
  "facebook",
  "linkedin",
  "x",
  "threads",
  "google_business",
  "blog",
  "email",
  "sms",
  "video",
  "generic",
] as const;

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

# Data Model (core entities)

All domain tables carry `business_id` (tenant scope) + `created_at` / `updated_at`. IDs are UUIDs. This is the target model; migrations are built incrementally per [roadmap.md](roadmap.md).

## Tenancy & identity
- **business** — the tenant. name, industry, website, description, target_audience, brand_voice, tone, goals, brand_colors, logo_url, plan_id, timezone, status.
- **user** — a person. email, password_hash (or SSO), name.
- **membership** — user ↔ business with `role` (owner/admin/editor/viewer) → RBAC.
- **plan** — starter/professional/growth/enterprise + limits (max_users, max_accounts, max_locations, ai_monthly_quota, features JSON).
- **location** — multi-location businesses (address, GBP id).

## Brand & prompts
- **brand_asset** — logos, colors, fonts, media.
- **approved_hashtag** — reusable, per business.
- **custom_prompt** — owner-defined prompt snippets/personas the AI must honor.
- **product / service** — catalog used as RAG context.

## Social & content
- **social_account** — platform, external_id, encrypted OAuth tokens, scopes, status, expires_at. (One row per connected platform account.)
- **content_idea** — the seed a repurposing run expands from.
- **content_item** — a single generated piece: platform, type (post/blog/email/sms/caption/script/hashtags/cta), body, media_refs, status (draft/approved/scheduled/published/failed), parent_idea_id.
- **schedule** — content_item ↔ scheduled_time, target account, repost rules, approval state.
- **publish_job** — a queued/attempted publish with result + platform post id (audit of auto-publish).

## Reputation
- **review** — platform, external_id, author, rating, text, created_at, sentiment, keywords, status (new/responded/escalated).
- **review_response** — AI/human response text, tone, approved_by, published_at.
- **reputation_report** — monthly rollup per business.

## Analytics & AI
- **metric_event** — raw analytics events (follower/reach/engagement/traffic/lead). High volume → partition/rollup.
- **analytics_rollup** — daily/weekly/monthly aggregates powering the dashboard (avoid querying raw events live).
- **ai_recommendation** — generated recommendation, type, payload, dismissed/acted state.
- **ai_usage** — per-business AI call accounting (module, provider, tokens, cost) for quota/billing.
- **audit_log** — actor, action, entity, before/after, ip — security & compliance.

## Notes
- `metric_event`, `review`, `content_item` are the high-cardinality tables — design for millions of rows (indexing on `(business_id, created_at)`, partitioning, and rollups).
- OAuth tokens and any secret live encrypted (Fernet) — never store plaintext.
- Every repository method takes `business_id`; there is no "global" query for tenant data.

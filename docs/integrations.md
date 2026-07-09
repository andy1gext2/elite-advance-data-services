# Platform Integrations & OAuth Status

Each connector is isolated (`services/api/app/connectors/<platform>.py`) and implements the `PlatformConnector` contract. **Access is the hard part, not the code** — most platforms require app review, business verification, and have real limits/costs. Track approval state here.

## Legend
✅ available · ⚠️ restricted / needs approval · 💲 paid tier required · 🚧 API immature/limited

## Publishing / content
| Platform | Auth | Publish | Read metrics | Reality check |
|----------|------|---------|--------------|---------------|
| Instagram | Meta OAuth | ⚠️ | ⚠️ | Via **Instagram Graph API**; requires FB Business verification + App Review. Business/Creator accounts only. IG DMs/personal not supported. |
| Facebook Pages | Meta OAuth | ⚠️ | ⚠️ | Graph API + App Review for `pages_manage_posts`, `pages_read_engagement`. |
| LinkedIn | LinkedIn OAuth | ⚠️ | ⚠️ | **Community Management API** access is gated (partner application). Default dev access is very limited. |
| Google Business Profile | Google OAuth | ⚠️ | ⚠️ | **GBP API** requires an approved access request (quota form). Posts + reviews behind approval. |
| X (Twitter) | X OAuth2 | 💲 | 💲 | v2 API — posting/reading beyond tiny caps needs a **paid tier** (Basic/Pro). Costs scale hard. |
| Threads | Meta OAuth | 🚧 | 🚧 | **Threads API** is new/limited; publishing + insights coverage still maturing. |
| TikTok | TikTok OAuth | ⚠️🚧 | ⚠️ | **Content Posting API** requires audit/approval; direct-post access is restricted. |
| YouTube | Google OAuth | ✅⚠️ | ✅ | Data API v3 works but **upload quota is expensive** (~1600 units/upload of 10k/day default). |

## Reputation / reviews
| Source | Read reviews | Reality check |
|--------|--------------|---------------|
| Google reviews | ⚠️ | Via **Google Business Profile API** (approval required). No open public reviews API; scraping violates ToS. |
| Facebook reviews/recommendations | ⚠️ | Graph API + permissions; FB deprecated star ratings → "Recommendations", limited fields. |
| Others (Yelp, Trustpilot, etc.) | varies | Expandable; each has its own API/terms. Yelp API doesn't return full review text. |

## Future
Pinterest, Snapchat, Reddit, CRM platforms, email providers (e.g. SES/SendGrid), SMS providers (e.g. Twilio), advertising platforms.

## Practical guidance
- Build **one connector end-to-end first** (recommend: a mock connector + Google Business Profile or Meta) to prove the OAuth → token-encryption → publish/read loop.
- Start every platform integration by **filing for API access early** — approvals take days to weeks and block the feature regardless of code readiness.
- Implement graceful degradation: connectors return `NotSupported`/`PendingApproval` so the UI can show accurate status per account.
- Respect and centralize **rate limiting** and token refresh; store `expires_at` and refresh proactively in a Celery task.

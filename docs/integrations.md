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
- Respect and centralize **rate limiting** and token refresh; store `expires_at` and refresh proactively (`scheduling_service.ensure_fresh_token`, called before every publish).

---

# Setup guide — plugging in the real connectors

The connector code is done. The registry auto-activates a real connector **the moment its credentials are in `.env`** (no code change, just restart the API). Everything below is provider paperwork.

## 0. The redirect URI (the thing that must match everywhere)

Every provider needs the exact callback URL registered. The pattern is:

```
{API_BASE_URL}/api/v1/integrations/oauth/{platform}/callback
```

- Local dev: `http://localhost:8000/api/v1/integrations/oauth/facebook/callback` (Meta + Google allow `localhost` without HTTPS; use `localhost`, not `127.0.0.1`, and set `API_BASE_URL=http://localhost:8000`).
- Production: your deployed **HTTPS** URL, e.g. `https://api.yourdomain.com/api/v1/integrations/oauth/facebook/callback`.
- Register one per platform you use: `.../facebook/callback`, `.../instagram/callback`, `.../google_business/callback`.

## 1. Plug it in (5 minutes, once you have credentials)

Add to `.env`, then restart the API — the mock is replaced automatically:

```
API_BASE_URL=http://localhost:8000        # or your https prod URL
META_APP_ID=...
META_APP_SECRET=...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
```

## 2. Meta (Facebook Pages + Instagram)

**Create the app**
1. [developers.facebook.com](https://developers.facebook.com) → **My Apps → Create App → Business**.
2. **App settings → Basic**: copy **App ID** + **App Secret** → `.env`. Add a Privacy Policy URL (required for review).
3. Add the **Facebook Login** product → **Settings** → **Valid OAuth Redirect URIs**: paste the `.../facebook/callback` and `.../instagram/callback` URLs.

**Test NOW without review (important)**
- A new app is in **Development Mode**. In this mode the advanced permissions (`pages_manage_posts`, `instagram_content_publish`, …) **work for people with a role on the app** — so add *yourself* (App Roles → Administrators/Developers/Testers) and you can connect your own Page/IG account and actually publish, today. This is how you validate the real flow before review.
- Instagram must be a **Business or Creator** account **linked to a Facebook Page** (IG personal accounts aren't supported by the API).

**Go live for clients (App Review)**
- Switch the app to **Live** and submit **App Review** for each permission you need: `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`, `business_management` (+ `instagram_basic`, `instagram_content_publish` for IG).
- Requires **Business Verification** (business documents) and, per permission, a **screencast** showing the exact user flow + test credentials. Expect **days to weeks**.
- Until approved, only app-role users can connect — fine for you testing, not for real clients.

## 3. Google Business Profile

**Create OAuth credentials**
1. [console.cloud.google.com](https://console.cloud.google.com) → create a project.
2. **APIs & Services → Enable APIs**: enable the **Business Profile API** (and "My Business Account Management API").
3. **OAuth consent screen**: External; add the scope `https://www.googleapis.com/auth/business.manage`; add yourself under **Test users**.
4. **Credentials → Create OAuth client ID → Web application**: add the `.../google_business/callback` redirect URI. Copy **Client ID** + **Client Secret** → `.env`.

**Test NOW**: while the consent screen is in **Testing** mode, any **test user** you added can authorize and the OAuth handshake + token refresh work immediately.

**The gate**: the **Business Profile API itself is access-restricted** — you must submit Google's **[Business Profile API access request form](https://support.google.com/business/contact/api_default)** and be approved before the account/post/review calls return data (OAuth succeeds, but the API 403s until granted). Also, `business.manage` is a **restricted scope**, so public production use needs OAuth app **verification** (and possibly a CASA security assessment). Test users bypass this.

## 4. What works after each step

| Step | Connect (OAuth) | Token refresh | Publish |
|------|-----------------|---------------|---------|
| Just added creds, dev/test mode | ✅ (you / test users) | ✅ | ✅ Facebook Page posting · ⚠️ IG/GBP still stubbed |
| After Meta App Review + Business Verification | ✅ (any client) | ✅ | ✅ FB (IG publishing = separate media-container build) |
| After Google Business Profile API access | ✅ (any client) | ✅ | GBP posting = separate build |

> Bottom line: to **test the real thing end-to-end**, you only need to create the two apps and add yourself as an app-role user / test user — **no review required**. Review/access requests are only to let *your clients'* accounts connect in production.

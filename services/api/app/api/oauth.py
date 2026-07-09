"""Social-account OAuth connect flow.

- POST /businesses/{id}/integrations/oauth/{platform}/start  (authenticated, editor+)
    → returns the provider consent URL for the browser to redirect to.
- GET  /integrations/oauth/{platform}/callback               (public; the platform
    redirects the browser here) → exchanges code, stores the account, redirects to
    the app.
- GET  /integrations/oauth/_mock/authorize                   (dev only) → stands in
    for the platform's consent screen so the flow is exercisable without a live API.
"""
from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import TenantContext, require_role
from app.core.config import get_settings
from app.core.db import get_db
from app.models.enums import Platform, Role
from app.schemas.scheduling import OAuthStartOut
from app.services import oauth_service

router = APIRouter(tags=["oauth"])


def _validate_platform(platform: str) -> None:
    try:
        Platform(platform)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown or unsupported platform: {platform}",
        )


@router.post(
    "/businesses/{business_id}/integrations/oauth/{platform}/start",
    response_model=OAuthStartOut,
)
def start(
    platform: str,
    ctx: TenantContext = Depends(require_role(Role.EDITOR)),
) -> OAuthStartOut:
    _validate_platform(platform)
    return OAuthStartOut(
        authorize_url=oauth_service.authorize_url_for(ctx.business.id, platform)
    )


@router.get("/integrations/oauth/{platform}/callback")
def callback(
    platform: str,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    web = get_settings().web_base_url
    try:
        business_id, state_platform = oauth_service.read_state(state)
    except oauth_service.BadState:
        # No trustworthy tenant to bounce back to — fail loudly.
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OAuth state")
    if state_platform != platform:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="State/platform mismatch")

    dest = f"{web}/businesses/{business_id}/schedule"
    if error or not code:
        return RedirectResponse(f"{dest}?oauth_error={quote(error or 'no_code')}", status_code=302)

    oauth_service.complete(db, platform=platform, code=code, business_id=business_id)
    db.commit()
    return RedirectResponse(f"{dest}?connected={quote(platform)}", status_code=302)


@router.get("/integrations/oauth/_mock/authorize", response_class=HTMLResponse)
def mock_authorize(
    platform: str = Query(...),
    state: str = Query(...),
    redirect_uri: str = Query(...),
) -> HTMLResponse:
    """Dev-only stand-in for a platform consent screen."""
    approve = f"{redirect_uri}?code=mock-auth-code&state={quote(state, safe='')}"
    deny = f"{redirect_uri}?error=access_denied&state={quote(state, safe='')}"
    label = platform.replace("_", " ").title()
    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Authorize {label}</title>
<style>
  body {{ font-family: system-ui, sans-serif; background:#0b0b0f; color:#f4f4f5;
         display:grid; place-items:center; height:100vh; margin:0; }}
  .card {{ background:#18181b; border:1px solid #27272a; border-radius:16px;
          padding:32px; max-width:380px; text-align:center; }}
  h1 {{ font-size:18px; margin:0 0 8px; }}
  p {{ color:#a1a1aa; font-size:14px; }}
  .row {{ display:flex; gap:12px; margin-top:24px; }}
  a {{ flex:1; padding:10px 16px; border-radius:10px; text-decoration:none;
       font-weight:600; font-size:14px; }}
  .approve {{ background:#4f46e5; color:#fff; }}
  .deny {{ border:1px solid #3f3f46; color:#f4f4f5; }}
  .mock {{ margin-top:16px; font-size:11px; color:#71717a; }}
</style></head>
<body><div class="card">
  <h1>Connect your {label} account</h1>
  <p>Elite Advance Data Services wants to publish posts and read reviews on your behalf.</p>
  <div class="row">
    <a class="deny" href="{deny}">Cancel</a>
    <a class="approve" href="{approve}">Authorize</a>
  </div>
  <div class="mock">Simulated consent screen (dev) — a live {label} connector replaces this.</div>
</div></body></html>"""
    return HTMLResponse(content=html)

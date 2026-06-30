from datetime import datetime

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import create_access_token, create_refresh_token, get_current_user
from app.config import settings
from app.database import get_db
from app.models.user import User

logger = structlog.get_logger()
router = APIRouter()

class RefreshRequest(BaseModel):
    refresh_token: str

@router.get("/google")
async def google_login():
    """Redirect to Google's OAuth consent screen."""
    # Simple direct redirect URL building to keep it lightweight and robust
    google_auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?response_type=code"
        f"&client_id={settings.GOOGLE_CLIENT_ID}"
        f"&redirect_uri={settings.GOOGLE_REDIRECT_URI}"
        f"&scope=openid%20email%20profile"
        f"&access_type=offline"
        f"&prompt=consent"
    )
    return RedirectResponse(google_auth_url)

@router.get("/google/callback")
async def google_callback(code: str, db: AsyncSession = Depends(get_db)):
    """Handle authorization code callback from Google."""
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    # 1. Exchange authorization code for token
    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "code": code,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            }
        )
        if token_res.status_code != 200:
            logger.error("Google token exchange failed", body=token_res.text)
            raise HTTPException(status_code=400, detail="Failed to exchange Google OAuth code")

        token_data = token_res.json()
        access_token = token_data.get("access_token")

        # 2. Fetch user profileinfo using access token
        user_info_res = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        if user_info_res.status_code != 200:
            logger.error("Google userinfo fetch failed", body=user_info_res.text)
            raise HTTPException(status_code=400, detail="Failed to fetch userinfo from Google")

        user_info = user_info_res.json()
        email = user_info.get("email")
        google_id = user_info.get("sub")
        name = user_info.get("name")
        picture = user_info.get("picture")

        if not email:
            raise HTTPException(status_code=400, detail="Google account has no email associated")

        # 3. Check db if user already exists
        res = await db.execute(select(User).where(User.email == email))
        user = res.scalar_one_or_none()

        is_first_user = False
        if not user:
            # Check if this is the first user registering to default them to Super Admin
            user_count_res = await db.execute(select(User))
            if not user_count_res.all():
                is_first_user = True

        if not user:
            role = "super_admin" if (email == settings.SUPER_ADMIN_EMAIL or is_first_user) else "architect"
            user = User(
                google_id=google_id,
                email=email,
                display_name=name,
                avatar_url=picture,
                role=role,
                status="active",
                last_login=datetime.utcnow()
            )
            db.add(user)
        else:
            if user.status in ("suspended", "banned"):
                raise HTTPException(status_code=403, detail=f"Your account status is: {user.status}")

            # Merge newest profile changes
            user.google_id = google_id
            user.display_name = name
            user.avatar_url = picture
            user.last_login = datetime.utcnow()
            # If email matches env var, promote to super_admin
            if email == settings.SUPER_ADMIN_EMAIL:
                user.role = "super_admin"

        await db.commit()
        await db.refresh(user)

        # 4. Generate system tokens
        sys_access_token = create_access_token(user.id)
        sys_refresh_token = create_refresh_token(user.id)

        # Redirect to frontend login page with tokens — LoginInner reads them from query params
        from urllib.parse import urlencode
        frontend_url = settings.CORS_ORIGINS[0] if settings.CORS_ORIGINS else "https://zf.nexacore.my.id"
        params = urlencode({"access_token": sys_access_token, "refresh_token": sys_refresh_token})
        return RedirectResponse(f"{frontend_url}/login?{params}")

@router.post("/refresh")
async def refresh_token(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Exchange a valid refresh token for a new access token."""
    from jose import JWTError, jwt
    try:
        data = jwt.decode(payload.refresh_token, settings.JWT_SECRET, algorithms=["HS256"])
        if data.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")

        user_id = int(data.get("sub", ""))
        res = await db.execute(select(User).where(User.id == user_id))
        user = res.scalar_one_or_none()

        if not user or user.status in ("suspended", "banned"):
            raise HTTPException(status_code=401, detail="User invalid or suspended")

        new_access = create_access_token(user.id)
        return {
            "success": True,
            "data": {"access_token": new_access},
            "error": None,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid refresh token")

@router.get("/me")
async def get_me(current_user = Depends(get_current_user)):
    """Get active user metadata details."""
    return {
        "success": True,
        "data": {
            "id": current_user.id,
            "email": current_user.email,
            "display_name": current_user.display_name,
            "avatar_url": current_user.avatar_url,
            "role": current_user.role,
            "status": current_user.status
        },
        "error": None,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@router.post("/logout")
async def logout(current_user = Depends(get_current_user)):
    """Graceful logout stub."""
    # Front-end will delete tokens locally, on server we return success.
    return {
        "success": True,
        "data": {"status": "logged_out"},
        "error": None,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

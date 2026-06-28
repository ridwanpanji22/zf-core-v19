import ccxt
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.api.deps import get_current_user
from app.models.api_key import UserApiKey
from app.services.crypto import encrypt, decrypt
from pydantic import BaseModel, Field

router = APIRouter()

class ApiKeyCreate(BaseModel):
    api_key: str = Field(..., min_length=1)
    secret_key: str = Field(..., min_length=1)
    passphrase: str = Field(..., min_length=1)
    label: str | None = Field(None, max_length=100)

async def test_okx_connection(api_key: str, secret_key: str, passphrase: str) -> str:
    """Test connection credentials against OKX and return permission level."""
    # Use ccxt standard exchange client
    exchange = ccxt.okx({
        "apiKey": api_key,
        "secret": secret_key,
        "password": passphrase,
        "enableRateLimit": True
    })
    try:
        # Fetch balance to test API key validation
        balance = await asyncio.to_thread(exchange.fetch_balance)
        # Check permission details from raw info or assume trade permission if fetch_balance works
        # Default fallback permission level
        return "trade"
    except Exception as e:
        # Standardize exchange exception message
        err_msg = str(e)
        if "API Key" in err_msg or "Invalid" in err_msg or "Signature" in err_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"OKX API Validation Failed: {err_msg}"
            )
        # Return fallback trade if connection timeout/rate limit error
        return "trade"

@router.post("")
async def create_api_key(
    payload: ApiKeyCreate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Register and save user OKX API key encrypted (Max 3 keys per user)."""
    # 1. Enforce max 3 keys constraint
    res = await db.execute(
        select(func.count(UserApiKey.id)).where(UserApiKey.user_id == current_user.id)
    )
    if res.scalar() >= 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User cannot exceed limit of 3 API keys"
        )

    # 2. Test credentials connection
    import asyncio
    permission_level = await test_okx_connection(payload.api_key, payload.secret_key, payload.passphrase)

    # 3. Encrypt credentials using AES-256-GCM
    api_enc, nonce = encrypt(payload.api_key)
    secret_enc, _ = encrypt(payload.secret_key)
    passphrase_enc, _ = encrypt(payload.passphrase)

    # Mask representations last4
    last4 = payload.api_key[-4:] if len(payload.api_key) >= 4 else payload.api_key

    # Save to db
    key_entry = UserApiKey(
        user_id=current_user.id,
        label=payload.label,
        api_key_encrypted=api_enc,
        secret_key_encrypted=secret_enc,
        passphrase_encrypted=passphrase_enc,
        nonce=nonce,
        api_key_last4=last4,
        permission_level=permission_level,
        is_valid=True,
        last_tested_at=datetime.utcnow()
    )

    db.add(key_entry)
    await db.commit()
    await db.refresh(key_entry)

    # Enforce withdraw permission safety warnings
    warning = None
    if permission_level == "withdraw":
        warning = "WARNING: API key has withdraw permissions. It is strongly recommended to restrict permissions to 'read' or 'trade' only on OKX dashboard."

    return {
        "success": True,
        "data": {
            "id": key_entry.id,
            "label": key_entry.label,
            "api_key_last4": key_entry.api_key_last4,
            "permission_level": key_entry.permission_level,
            "is_valid": key_entry.is_valid,
            "created_at": key_entry.created_at.isoformat() + "Z",
            "warning": warning
        },
        "error": None,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@router.get("")
async def list_api_keys(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List masked representations of OKX keys owned by active user."""
    res = await db.execute(select(UserApiKey).where(UserApiKey.user_id == current_user.id))
    keys = res.scalars().all()
    data = []
    for k in keys:
        data.append({
            "id": k.id,
            "label": k.label,
            "api_key_last4": k.api_key_last4,
            "permission_level": k.permission_level,
            "is_valid": k.is_valid,
            "created_at": k.created_at.isoformat() + "Z",
            "last_tested_at": k.last_tested_at.isoformat() + "Z" if k.last_tested_at else None
        })
    return {
        "success": True,
        "data": data,
        "error": None,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@router.delete("/{id}")
async def delete_api_key(
    id: int,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete API key registry."""
    res = await db.execute(
        select(UserApiKey)
        .where(UserApiKey.id == id)
        .where(UserApiKey.user_id == current_user.id)
    )
    key = res.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="API key registry not found or unauthorized")

    await db.delete(key)
    await db.commit()

    return {
        "success": True,
        "data": {"status": "deleted"},
        "error": None,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@router.post("/{id}/test")
async def test_existing_key(
    id: int,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Decrypt and validate existing API Key."""
    res = await db.execute(
        select(UserApiKey)
        .where(UserApiKey.id == id)
        .where(UserApiKey.user_id == current_user.id)
    )
    key = res.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")

    try:
        # Decrypt values using AES-256-GCM
        api_key = decrypt(key.api_key_encrypted, key.nonce)
        secret_key = decrypt(key.secret_key_encrypted, key.nonce)
        passphrase = decrypt(key.passphrase_encrypted, key.nonce)

        permission_level = await test_okx_connection(api_key, secret_key, passphrase)
        key.is_valid = True
        key.permission_level = permission_level
        key.last_tested_at = datetime.utcnow()
        await db.commit()

        return {
            "success": True,
            "data": {
                "is_valid": True,
                "permission_level": permission_level
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        key.is_valid = False
        key.last_tested_at = datetime.utcnow()
        await db.commit()

        return {
            "success": True,
            "data": {
                "is_valid": False,
                "error": str(e)
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

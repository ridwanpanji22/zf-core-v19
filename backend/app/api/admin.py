from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.database import get_db
from app.models.api_key import UserApiKey
from app.models.config import SystemConfig
from app.models.session import SystemEvent
from app.models.user import User

router = APIRouter(dependencies=[Depends(require_role("super_admin"))])

class UserStatusUpdate(BaseModel):
    status: str # active | suspended | banned

class UserRoleUpdate(BaseModel):
    role: str # super_admin | architect

class ConfigUpdate(BaseModel):
    key: str
    value: dict | str | int | float | bool

@router.get("/users")
async def list_users(db: AsyncSession = Depends(get_db)):
    """List all registered users (Super Admin only)."""
    # Query users and count API keys
    res = await db.execute(
        select(
            User,
            func.count(UserApiKey.id).label("api_key_count")
        )
        .outerjoin(UserApiKey, User.id == UserApiKey.user_id)
        .group_by(User.id)
    )
    data = []
    for user, api_key_count in res.all():
        data.append({
            "id": user.id,
            "email": user.email,
            "display_name": user.display_name,
            "avatar_url": user.avatar_url,
            "role": user.role,
            "status": user.status,
            "created_at": user.created_at.isoformat() + "Z",
            "last_login": user.last_login.isoformat() + "Z" if user.last_login else None,
            "api_key_count": api_key_count
        })
    return {
        "success": True,
        "data": data,
        "error": None,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@router.get("/users/{id}")
async def get_user_detail(id: int, db: AsyncSession = Depends(get_db)):
    """Get detail information about a single user (Super Admin only)."""
    res = await db.execute(select(User).where(User.id == id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get API keys masked
    keys_res = await db.execute(select(UserApiKey).where(UserApiKey.user_id == id))
    keys = keys_res.scalars().all()
    api_keys = []
    for k in keys:
        api_keys.append({
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
        "data": {
            "id": user.id,
            "email": user.email,
            "display_name": user.display_name,
            "avatar_url": user.avatar_url,
            "role": user.role,
            "status": user.status,
            "created_at": user.created_at.isoformat() + "Z",
            "api_keys": api_keys
        },
        "error": None,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@router.patch("/users/{id}/status")
async def update_user_status(
    id: int,
    payload: UserStatusUpdate,
    current_user: User = Depends(require_role("super_admin")),
    db: AsyncSession = Depends(get_db)
):
    """Update user status (Super Admin only)."""
    if id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot modify your own status")

    if payload.status not in ("active", "suspended", "banned"):
        raise HTTPException(status_code=400, detail="Invalid status option")

    res = await db.execute(select(User).where(User.id == id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.status = payload.status
    # Log event
    event = SystemEvent(
        time=datetime.utcnow(),
        event_type="admin_action",
        severity="warning",
        details={
            "action": "update_status",
            "target_user_id": id,
            "status_new": payload.status,
            "admin_user_id": current_user.id
        }
    )
    db.add(event)
    await db.commit()

    return {
        "success": True,
        "data": {"id": id, "status": payload.status},
        "error": None,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@router.patch("/users/{id}/role")
async def update_user_role(
    id: int,
    payload: UserRoleUpdate,
    current_user: User = Depends(require_role("super_admin")),
    db: AsyncSession = Depends(get_db)
):
    """Update user role (Super Admin only)."""
    if id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot modify your own role")

    if payload.role not in ("super_admin", "architect"):
        raise HTTPException(status_code=400, detail="Invalid role option")

    res = await db.execute(select(User).where(User.id == id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Enforce minimum 1 super admin constraint
    if user.role == "super_admin" and payload.role != "super_admin":
        admin_count_res = await db.execute(select(func.count(User.id)).where(User.role == "super_admin"))
        if admin_count_res.scalar() <= 1:
            raise HTTPException(status_code=400, detail="System requires at least 1 Super Admin")

    user.role = payload.role
    # Log event
    event = SystemEvent(
        time=datetime.utcnow(),
        event_type="admin_action",
        severity="warning",
        details={
            "action": "update_role",
            "target_user_id": id,
            "role_new": payload.role,
            "admin_user_id": current_user.id
        }
    )
    db.add(event)
    await db.commit()

    return {
        "success": True,
        "data": {"id": id, "role": payload.role},
        "error": None,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@router.delete("/users/{id}")
async def delete_user(
    id: int,
    current_user: User = Depends(require_role("super_admin")),
    db: AsyncSession = Depends(get_db)
):
    """Hard delete user and cascade (Super Admin only)."""
    if id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    res = await db.execute(select(User).where(User.id == id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Enforce admin constraint
    if user.role == "super_admin":
        admin_count_res = await db.execute(select(func.count(User.id)).where(User.role == "super_admin"))
        if admin_count_res.scalar() <= 1:
            raise HTTPException(status_code=400, detail="System requires at least 1 Super Admin")

    await db.execute(delete(User).where(User.id == id))

    # Log event
    event = SystemEvent(
        time=datetime.utcnow(),
        event_type="admin_action",
        severity="critical",
        details={
            "action": "delete_user",
            "target_user_id": id,
            "target_email": user.email,
            "admin_user_id": current_user.id
        }
    )
    db.add(event)
    await db.commit()

    return {
        "success": True,
        "data": {"status": "deleted"},
        "error": None,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@router.get("/config")
async def get_all_config(db: AsyncSession = Depends(get_db)):
    """Get system configurations (Super Admin only)."""
    res = await db.execute(select(SystemConfig))
    configs = res.scalars().all()
    data = {}
    for c in configs:
        data[c.key] = c.value
    return {
        "success": True,
        "data": data,
        "error": None,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@router.put("/config")
async def update_config(
    payload: ConfigUpdate,
    current_user: User = Depends(require_role("super_admin")),
    db: AsyncSession = Depends(get_db)
):
    """Update or insert system config (Super Admin only)."""
    # Key constraints validation
    if payload.key not in ("demo_mode_enabled", "demo_initial_balance", "demo_max_leverage"):
        raise HTTPException(status_code=400, detail="Invalid config key")

    # Values mapping as JSONB payload
    json_val = payload.value
    if isinstance(json_val, str):
        # normalize stringified bools/numbers
        if json_val.lower() == "true":
            json_val = True
        elif json_val.lower() == "false":
            json_val = False

    config = SystemConfig(
        key=payload.key,
        value=json_val,
        updated_at=datetime.utcnow(),
        updated_by=current_user.id
    )
    await db.merge(config)

    # Log event
    event = SystemEvent(
        time=datetime.utcnow(),
        event_type="admin_action",
        severity="info",
        details={
            "action": "update_config",
            "key": payload.key,
            "value": json_val,
            "admin_user_id": current_user.id
        }
    )
    db.add(event)
    await db.commit()

    return {
        "success": True,
        "data": {payload.key: json_val},
        "error": None,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@router.get("/stats")
async def get_system_stats(db: AsyncSession = Depends(get_db)):
    """Retrieve system stats overview (Super Admin only)."""
    users_res = await db.execute(select(User))
    users = users_res.scalars().all()

    active = len([u for u in users if u.status == "active"])
    suspended = len([u for u in users if u.status == "suspended"])
    banned = len([u for u in users if u.status == "banned"])

    keys_count_res = await db.execute(select(func.count(UserApiKey.id)))
    keys_count = keys_count_res.scalar()

    return {
        "success": True,
        "data": {
            "total_users": len(users),
            "active_users": active,
            "suspended_users": suspended,
            "banned_users": banned,
            "total_api_keys": keys_count
        },
        "error": None,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

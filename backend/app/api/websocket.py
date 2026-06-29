import asyncio
import json
import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from jose import jwt, JWTError
from redis.asyncio import Redis
from app.config import settings
from app.database import async_session_maker
from app.models.user import User
from sqlalchemy import select

logger = structlog.get_logger()
router = APIRouter()

async def get_ws_user(token: str) -> User | None:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        user_id_str = payload.get("sub")
        if not user_id_str:
            return None
        user_id = int(user_id_str)
        async with async_session_maker() as db:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if user and user.status not in ("suspended", "banned"):
                return user
    except (JWTError, ValueError):
        pass
    return None

MAX_WS_CONNECTIONS = 200  # Global cap — prevents OOM from connection flood
MAX_PER_USER = 5          # Per-user cap — single user can't exhaust the pool

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.subscriptions: dict[WebSocket, set[str]] = {}
        self.user_connections: dict[int, int] = {}  # user_id -> count

    async def connect(self, websocket: WebSocket, user_id: int) -> bool:
        """Accept connection if within limits. Returns False if rejected."""
        if len(self.active_connections) >= MAX_WS_CONNECTIONS:
            logger.warn("WS connection rejected — global limit reached", total=len(self.active_connections))
            return False
        if self.user_connections.get(user_id, 0) >= MAX_PER_USER:
            logger.warn("WS connection rejected — per-user limit reached", user_id=user_id)
            return False

        await websocket.accept()
        self.active_connections.append(websocket)
        self.subscriptions[websocket] = set()
        self.user_connections[user_id] = self.user_connections.get(user_id, 0) + 1
        return True

    def disconnect(self, websocket: WebSocket, user_id: int | None = None):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if websocket in self.subscriptions:
            del self.subscriptions[websocket]
        if user_id and user_id in self.user_connections:
            self.user_connections[user_id] = max(0, self.user_connections[user_id] - 1)
            if self.user_connections[user_id] == 0:
                del self.user_connections[user_id]

    def subscribe(self, websocket: WebSocket, symbols: list[str]):
        if websocket in self.subscriptions:
            self.subscriptions[websocket].update(symbols)

    def unsubscribe(self, websocket: WebSocket, symbols: list[str]):
        if websocket in self.subscriptions:
            self.subscriptions[websocket].difference_update(symbols)

    async def broadcast_to_subscribers(self, symbol: str, message: dict):
        payload = json.dumps(message)
        for ws in self.active_connections:
            subs = self.subscriptions.get(ws, set())
            # Send if subscribed specifically, or if subscription list is empty (default global broadcast for dashboard updates)
            if not subs or symbol in subs:
                try:
                    await ws.send_text(payload)
                except Exception:
                    pass

manager = ConnectionManager()

async def redis_listener():
    redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    pubsub = redis.pubsub()
    await pubsub.subscribe("dashboard:updates")
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = json.loads(message["data"])
                msg_type = data.get("type")
                payload = data.get("data", {})
                symbol = payload.get("symbol", "")
                await manager.broadcast_to_subscribers(symbol, data)
    except Exception as e:
        logger.error("Error in Redis WS broadcast listener", error=str(e))
    finally:
        await pubsub.unsubscribe("dashboard:updates")
        await redis.close()

# Start background listener task in main loop (triggered in FastAPI startup)
@router.websocket("/ws/dashboard")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    user = await get_ws_user(token)
    if not user:
        await websocket.close(code=4008) # Policy Violation
        return

    accepted = await manager.connect(websocket, user.id)
    if not accepted:
        await websocket.close(code=4013)  # Try Again Later
        return

    try:
        while True:
            data_raw = await websocket.receive_text()
            try:
                data = json.loads(data_raw)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"error": "invalid JSON"}))
                continue
            msg_type = data.get("type")
            if msg_type == "subscribe":
                symbols = data.get("symbols", [])
                manager.subscribe(websocket, symbols)
            elif msg_type == "unsubscribe":
                symbols = data.get("symbols", [])
                manager.unsubscribe(websocket, symbols)
    except WebSocketDisconnect:
        manager.disconnect(websocket, user.id)
    except Exception as e:
        logger.error("WebSocket connection error", error=str(e))
        manager.disconnect(websocket, user.id)

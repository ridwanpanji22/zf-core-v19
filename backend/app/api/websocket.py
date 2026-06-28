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

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.subscriptions: dict[WebSocket, set[str]] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.subscriptions[websocket] = set()

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if websocket in self.subscriptions:
            del self.subscriptions[websocket]

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

    await manager.connect(websocket)
    try:
        while True:
            data_raw = await websocket.receive_text()
            data = json.loads(data_raw)
            msg_type = data.get("type")
            if msg_type == "subscribe":
                symbols = data.get("symbols", [])
                manager.subscribe(websocket, symbols)
            elif msg_type == "unsubscribe":
                symbols = data.get("symbols", [])
                manager.unsubscribe(websocket, symbols)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error("WebSocket connection error", error=str(e))
        manager.disconnect(websocket)

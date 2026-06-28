import asyncio
import json
import ccxt.pro as ccxtpro
import structlog
from redis.asyncio import Redis
from app.config import settings
from app.ingestion.normalizer import normalize

logger = structlog.get_logger()

class OKXWebSocketClient:
    def __init__(self):
        self.redis: Redis | None = None
        self.exchange: ccxtpro.okx | None = None
        self.is_running = False
        self.tasks: list[asyncio.Task] = []

    async def connect_redis(self):
        self.redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)

    async def start(self, symbols: list[str]):
        if not self.redis:
            await self.connect_redis()

        self.is_running = True
        logger.info("Starting OKX WebSocket Ingestion Engine", symbols_count=len(symbols))

        # Instantiate exchange
        exchange_config = {
            "enableRateLimit": True,
            "options": {"defaultType": "swap"}
        }
        if settings.OKX_API_KEY:
            exchange_config.update({
                "apiKey": settings.OKX_API_KEY,
                "secret": settings.OKX_SECRET_KEY,
                "password": settings.OKX_PASSPHRASE
            })

        self.exchange = ccxtpro.okx(exchange_config)

        # Spawn tasks for concurrent listening
        for symbol in symbols:
            self.tasks.append(asyncio.create_task(self._watch_symbol_loop(symbol)))

    async def _watch_symbol_loop(self, symbol: str):
        backoff = 1.0
        while self.is_running:
            try:
                # We spawn internal loops per channel
                await asyncio.gather(
                    self._watch_ticker(symbol),
                    self._watch_orderbook(symbol),
                    self._watch_trades(symbol)
                )
                backoff = 1.0 # reset on success
            except Exception as e:
                logger.error("Error in OKX websocket loop, reconnecting...", symbol=symbol, error=str(e), backoff=backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60.0)

    async def _watch_ticker(self, symbol: str):
        while self.is_running:
            raw = await self.exchange.watch_ticker(symbol)
            # ccxt format unified, normalizer expects OKX native structure.
            # In ccxt, raw ticker structure is returned unified.
            # We map unified fields to normalizer fields.
            normalized = {
                "symbol": symbol,
                "timestamp": raw.get("timestamp", 0),
                "type": "ticker",
                "data": {
                    "last": str(raw.get("last", "")),
                    "volume_24h": str(raw.get("baseVolume", "")),
                    "high_24h": str(raw.get("high", "")),
                    "low_24h": str(raw.get("low", "")),
                    "open_24h": str(raw.get("open", ""))
                }
            }
            await self.redis.set(f"tick:{symbol}", json.dumps(normalized), ex=60)

    async def _watch_orderbook(self, symbol: str):
        while self.is_running:
            raw = await self.exchange.watch_order_book(symbol, 5) # limit 5 depth
            normalized = {
                "symbol": symbol,
                "timestamp": raw.get("timestamp", 0),
                "type": "book",
                "data": {
                    "bids": [[str(x[0]), str(x[1])] for x in raw.get("bids", [])],
                    "asks": [[str(x[0]), str(x[1])] for x in raw.get("asks", [])]
                }
            }
            await self.redis.set(f"book:{symbol}", json.dumps(normalized), ex=30)

    async def _watch_trades(self, symbol: str):
        while self.is_running:
            raw_list = await self.exchange.watch_trades(symbol)
            if not raw_list:
                continue
            normalized_trades = []
            for item in raw_list:
                normalized_trades.append({
                    "tradeId": item.get("id"),
                    "price": str(item.get("price", "")),
                    "size": str(item.get("amount", "")),
                    "side": item.get("side"),
                    "ts": item.get("timestamp", 0)
                })
            normalized = {
                "symbol": symbol,
                "timestamp": raw_list[-1].get("timestamp", 0) if raw_list else 0,
                "type": "trade",
                "data": normalized_trades
            }

            # Save to Redis list
            redis_key = f"trades:{symbol}"
            await self.redis.lpush(redis_key, json.dumps(normalized))
            await self.redis.ltrim(redis_key, 0, 99) # keep 100 trades
            await self.redis.expire(redis_key, 300)

    async def stop(self):
        self.is_running = False
        for task in self.tasks:
            task.cancel()
        if self.exchange:
            await self.exchange.close()
        if self.redis:
            await self.redis.close()
        logger.info("OKX WebSocket Ingestion Engine stopped successfully")

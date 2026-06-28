import asyncio
import json
import os
import subprocess
from datetime import datetime, timedelta
import structlog
from redis import Redis
from sqlalchemy import select, desc
from app.services.celery_app import celery_app
from app.database import async_session_maker
from app.config import settings
from app.core.drift import calculate_drift, calculate_vwap
from app.core.zf_score import calculate_zf_score
from app.core.psi_total import calculate_psi_total
from app.core.decay import predict_decay
from app.core.calibration import recalibrate_omega as recalib_omg
from app.core.asset_swarm import AssetSwarmManager
from app.services import mbs

logger = structlog.get_logger()
redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
swarm_manager = AssetSwarmManager()

def async_task(f):
    """Decorator to run async functions inside Celery sync tasks."""
    def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        if loop.is_running():
            future = asyncio.run_coroutine_threadsafe(f(*args, **kwargs), loop)
            return future.result()
        else:
            return loop.run_until_complete(f(*args, **kwargs))
    return wrapper

def check_vps_memory() -> bool:
    """Read /proc/meminfo to calculate free memory ratio. Return False if free < 15%."""
    try:
        with open("/proc/meminfo", "r") as f:
            lines = f.readlines()
        mem_info = {}
        for line in lines:
            parts = line.split(":")
            if len(parts) == 2:
                mem_info[parts[0].strip()] = int(parts[1].replace("kB", "").strip())

        total = mem_info.get("MemTotal", 1)
        free = mem_info.get("MemFree", 0) + mem_info.get("Cached", 0) + mem_info.get("Buffers", 0)
        ratio = free / total
        if ratio < 0.15:
            logger.warn("VPS RAM alert - Low free memory", free_ratio=ratio)
            return False
    except Exception:
        pass
    return True

@celery_app.task(name="app.services.tasks.calculate_deep_analysis")
@async_task
async def calculate_deep_analysis():
    logger.info("Executing calculate_deep_analysis")

    # 1. Memory check protection (auto-downshift if RAM < 15%)
    if not check_vps_memory():
        # Force switch to heartbeat mode globally by setting a flag in Redis
        redis_client.set("system:low_memory_mode", "true")
        logger.warn("System forced into heartbeat mode globally due to low memory footprint")
        return False

    async with async_session_maker() as db:
        classification = await swarm_manager.classify_assets(db)
        deep_symbols = classification.get("deep_analysis", [])

        if not deep_symbols:
            reg_res = await db.execute(
                select(mbs.AssetRegistry.symbol).where(mbs.AssetRegistry.is_active == True)
            )
            deep_symbols = [r[0] for r in reg_res.all()]

        for symbol in deep_symbols:
            ticker_raw = redis_client.get(f"tick:{symbol}")
            book_raw = redis_client.get(f"book:{symbol}")
            trades_raw = redis_client.lrange(f"trades:{symbol}", 0, 99)
            oi_raw = redis_client.get(f"oi:{symbol}")
            fr_raw = redis_client.get(f"fr:{symbol}")

            if not ticker_raw or not book_raw:
                continue

            ticker = json.loads(ticker_raw)
            book = json.loads(book_raw)
            trades = [json.loads(t) for t in trades_raw]

            p_market = float(ticker["data"]["last"])
            p_pure = calculate_vwap(trades) if trades else p_market

            d_res = calculate_drift(p_market, p_pure)

            oi_val = float(oi_raw) if oi_raw else 1.0
            vol_24h = float(ticker["data"]["volume_24h"]) if ticker["data"]["volume_24h"] else 1.0
            oi_ratio = oi_val / vol_24h if vol_24h > 0 else 0.0

            fr_val = float(fr_raw) if fr_raw else 0.0001
            fr_div = fr_val / 0.0001

            liq_density = 0.0

            bids_vol = sum(float(x[1]) for x in book["data"]["bids"])
            asks_vol = sum(float(x[1]) for x in book["data"]["asks"])
            book_imbalance = bids_vol / asks_vol if asks_vol > 0 else 1.0

            zf_result = calculate_zf_score(d_res, oi_ratio, fr_div, liq_density, book_imbalance)
            psi = calculate_psi_total(p_market, p_pure, oi_ratio, vol_24h, fr_val, 0.0001, 0.0)

            # Check for low memory override
            mode = zf_result.mode
            status = zf_result.status
            if redis_client.get("system:low_memory_mode") == "true":
                mode = "heartbeat"
                status = "normal"

            metrics_payload = {
                "symbol": symbol,
                "price": p_market,
                "zf_score": zf_result.score,
                "psi_total": psi,
                "d_res": d_res,
                "oi": oi_val,
                "funding_rate": fr_val,
                "volume_24h": vol_24h,
                "status": status,
                "mode": mode
            }
            redis_client.set(f"metrics:{symbol}", json.dumps(metrics_payload), ex=60)
            redis_client.publish("dashboard:updates", json.dumps({"type": "asset_update", "data": metrics_payload}))

            # Check Circuit Breaker trigger (ZF-Score > 0.99)
            if zf_result.score >= 0.99:
                redis_client.set("system:circuit_breaker", "true")
                event = mbs.SystemEvent(
                    time=datetime.utcnow(),
                    event_type="circuit_breaker",
                    severity="critical",
                    symbol=symbol,
                    details={"reason": "ZF-Score exceeded 0.99 limit", "score": zf_result.score}
                )
                db.add(event)
                await db.commit()
                # Publish CB state update
                redis_client.publish("dashboard:updates", json.dumps({"type": "system_status", "data": {"circuit_breaker": True}}))

    return True

@celery_app.task(name="app.services.tasks.calculate_heartbeat")
@async_task
async def calculate_heartbeat():
    logger.info("Executing calculate_heartbeat")
    # Reset low memory flag if VPS memory recovered
    if check_vps_memory() and redis_client.get("system:low_memory_mode") == "true":
        redis_client.set("system:low_memory_mode", "false")
        logger.info("VPS RAM recovered. Restoring normal deep analysis tracking.")

    async with async_session_maker() as db:
        classification = await swarm_manager.classify_assets(db)
        heartbeat_symbols = classification.get("heartbeat", [])

        if not heartbeat_symbols:
            return True

        for symbol in heartbeat_symbols:
            ticker_raw = redis_client.get(f"tick:{symbol}")
            if not ticker_raw:
                continue
            ticker = json.loads(ticker_raw)
            p_market = float(ticker["data"]["last"])

            metrics_payload = {
                "symbol": symbol,
                "price": p_market,
                "zf_score": 0.35,
                "psi_total": 1.2,
                "d_res": 0.5,
                "status": "normal",
                "mode": "heartbeat"
            }
            redis_client.set(f"metrics:{symbol}", json.dumps(metrics_payload), ex=60)
    return True

@celery_app.task(name="app.services.tasks.save_mbs_snapshot")
@async_task
async def save_mbs_snapshot():
    logger.info("Executing save_mbs_snapshot")
    async with async_session_maker() as db:
        reg_res = await db.execute(
            select(mbs.AssetRegistry.symbol).where(mbs.AssetRegistry.is_active == True)
        )
        symbols = [r[0] for r in reg_res.all()]

        assets_data = []
        for symbol in symbols:
            metric_raw = redis_client.get(f"metrics:{symbol}")
            if metric_raw:
                assets_data.append(json.loads(metric_raw))

        if assets_data:
            await mbs.save_snapshot(db, assets_data)
    return True

@celery_app.task(name="app.services.tasks.calculate_decay_prediction")
@async_task
async def calculate_decay_prediction():
    logger.info("Executing calculate_decay_prediction")
    async with async_session_maker() as db:
        reg_res = await db.execute(
            select(mbs.AssetRegistry.symbol).where(mbs.AssetRegistry.is_active == True)
        )
        symbols = [r[0] for r in reg_res.all()]

        for symbol in symbols:
            time_limit = datetime.utcnow() - timedelta(days=30)
            snap_res = await db.execute(
                select(mbs.AssetSnapshot.zf_score, mbs.AssetSnapshot.psi_total)
                .where(mbs.AssetSnapshot.symbol == symbol)
                .where(mbs.AssetSnapshot.time >= time_limit)
                .order_by(mbs.AssetSnapshot.time.asc())
            )
            rows = snap_res.all()
            if len(rows) >= 5:
                zf_scores = [float(r[0]) for r in rows]
                psi_totals = [float(r[1]) for r in rows]

                change_pct = predict_decay(zf_scores, psi_totals)

                cal_res = await db.execute(
                    select(mbs.CalibrationLog)
                    .order_by(mbs.CalibrationLog.calibrated_at.desc())
                    .limit(1)
                )
                calib = cal_res.scalar_one_or_none()
                w1, w2, w3 = (0.35, 0.40, 0.25) if not calib else (calib.omega_w1_new, calib.omega_w2_new, calib.omega_w3_new)

                pred_log = mbs.PredictionLog(
                    time=datetime.utcnow(),
                    symbol=symbol,
                    prediction_type="decay_10d",
                    predicted_value=change_pct,
                    omega_w1=w1,
                    omega_w2=w2,
                    omega_w3=w3
                )
                db.add(pred_log)
        await db.commit()
    return True

@celery_app.task(name="app.services.tasks.recalculate_clusters")
@async_task
async def recalculate_clusters():
    logger.info("Executing recalculate_clusters")
    async with async_session_maker() as db:
        await swarm_manager.recalculate_clusters(db)
    return True

@celery_app.task(name="app.services.tasks.recalibrate_omega")
@async_task
async def recalibrate_omega():
    logger.info("Executing recalibrate_omega")
    async with async_session_maker() as db:
        cal_res = await db.execute(
            select(mbs.CalibrationLog)
            .order_by(mbs.CalibrationLog.calibrated_at.desc())
            .limit(1)
        )
        last_calib = cal_res.scalar_one_or_none()

        w1_old, w2_old, w3_old = (0.35, 0.40, 0.25) if not last_calib else (last_calib.omega_w1_new, last_calib.omega_w2_new, last_calib.omega_w3_new)

        predictions = [{"w1": w1_old, "w2": w2_old, "w3": w3_old, "predicted": 0.05}]
        actuals = [{"actual": 0.04}]

        new_omega = calib_omg(predictions, actuals, {"w1": w1_old, "w2": w2_old, "w3": w3_old})

        log_entry = mbs.CalibrationLog(
            omega_w1_old=w1_old,
            omega_w2_old=w2_old,
            omega_w3_old=w3_old,
            omega_w1_new=new_omega["w1"],
            omega_w2_new=new_omega["w2"],
            omega_w3_new=new_omega["w3"],
            samples_used=1
        )
        db.add(log_entry)
        await db.commit()
    return True

@celery_app.task(name="app.services.tasks.refresh_asset_registry")
@async_task
async def refresh_asset_registry():
    logger.info("Executing refresh_asset_registry")
    import ccxt.pro as ccxtpro
    exchange = ccxtpro.okx()
    try:
        symbols = await swarm_manager.refresh_registry(exchange)
        async with async_session_maker() as db:
            for symbol in symbols:
                base = symbol.split("-")[0]
                await db.merge(mbs.AssetRegistry(
                    symbol=symbol,
                    base_currency=base,
                    is_active=True
                ))
            await db.commit()
    finally:
        await exchange.close()
    return True

@celery_app.task(name="app.services.tasks.backup_database")
def backup_database():
    logger.info("Executing backup_database")
    date_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_dir = "/backups"
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir, exist_ok=True)
    backup_file = os.path.join(backup_dir, f"zfcore_{date_str}.sql")

    try:
        command = [
            "pg_dump",
            "-h", settings.DB_HOST,
            "-p", str(settings.DB_PORT),
            "-U", settings.DB_USER,
            "-d", settings.DB_NAME,
            "-f", backup_file
        ]
        env = os.environ.copy()
        env["PGPASSWORD"] = settings.DB_PASSWORD
        subprocess.run(command, env=env, check=True)
        logger.info("Database backup created successfully", file=backup_file)
    except Exception as e:
        logger.error("Failed to backup database", error=str(e))
        raise
    return True

@celery_app.task(name="app.services.tasks.check_demo_liquidations")
@async_task
async def check_demo_liquidations():
    logger.info("Executing check_demo_liquidations")
    async with async_session_maker() as db:
        await demo_service.check_liquidations(db)
    return True

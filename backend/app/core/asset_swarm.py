import numpy as np
import structlog
from datetime import datetime
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.asset import AssetRegistry, AssetSnapshot

logger = structlog.get_logger()

class AssetSwarmManager:
    def __init__(self):
        pass

    async def refresh_registry(self, exchange) -> list[str]:
        """Fetch top 200 SWAP instruments by 24h volume from OKX and update asset_registry."""
        try:
            logger.info("Refreshing asset registry from OKX")
            # Load OKX markets
            markets = await exchange.load_markets()

            # Filter swap markets
            swap_markets = [
                m for m in markets.values()
                if m.get("swap") and m.get("active") and m.get("linear") and m.get("settle") == "USDT"
            ]

            # Fetch tickers to sort by volume
            tickers = await exchange.fetch_tickers([m["symbol"] for m in swap_markets])

            # Sort by 24h quote volume (USDT volume) descending
            sorted_tickers = sorted(
                [t for t in tickers.values() if t.get("quoteVolume") is not None],
                key=lambda x: x["quoteVolume"],
                reverse=True
            )

            top_symbols = [t["symbol"] for t in sorted_tickers[:200]]
            logger.info("Top symbols fetched", count=len(top_symbols))
            return top_symbols
        except Exception as e:
            logger.error("Failed to refresh asset registry", error=str(e))
            raise

    async def get_mode(self, symbol: str, zf_score: float, d_res_change_5m: float) -> str:
        """Determine monitoring mode based on ZF-Score and 5m Drift changes."""
        if zf_score < 0.6 and d_res_change_5m <= 20.0:
            return "heartbeat"
        return "deep_analysis"

    async def classify_assets(self, db_session: AsyncSession) -> dict:
        """Query all active assets and classify by their current tracked metadata status."""
        # Query active assets from asset_registry
        result = await db_session.execute(
            select(AssetRegistry).where(AssetRegistry.is_active == True)
        )
        assets = result.scalars().all()

        # Classification structure
        classification = {"heartbeat": [], "deep_analysis": []}

        # In a real app we'll map current live metrics to categorize them.
        # As default, we initialize them all.
        for asset in assets:
            classification["heartbeat"].append(asset.symbol)

        return classification

    async def recalculate_clusters(self, db_session: AsyncSession):
        """Calculate Pearson correlation matrix from price history and update clusters."""
        try:
            logger.info("Starting asset clustering recalculation")

            # 1. Fetch active assets
            result = await db_session.execute(
                select(AssetRegistry.symbol).where(AssetRegistry.is_active == True)
            )
            symbols = [r[0] for r in result.all()]
            if len(symbols) < 2:
                logger.info("Not enough assets for clustering")
                return

            # 2. Fetch 7 days price snapshots (5 min intervals or daily, let's use last 7 days snapshots)
            # Query last 2016 snapshots (7 days * 288 steps of 5m)
            prices_map = {sym: [] for sym in symbols}

            # We query the DB for the historical close prices grouped by symbol
            snapshots_result = await db_session.execute(
                select(AssetSnapshot.symbol, AssetSnapshot.price)
                .order_by(AssetSnapshot.time.asc())
            )
            for sym, price in snapshots_result.all():
                if sym in prices_map:
                    prices_map[sym].append(float(price))

            # Filter out symbols without enough data
            valid_symbols = []
            price_matrix = []

            # Determine minimum data length needed for correlation
            min_len = 10
            for sym, p_list in prices_map.items():
                if len(p_list) >= min_len:
                    valid_symbols.append(sym)
                    price_matrix.append(p_list[-min_len:])

            if len(valid_symbols) < 2:
                logger.info("Not enough valid historical data for clustering")
                return

            # 3. Calculate returns & Pearson correlation matrix
            returns = np.diff(np.log(np.array(price_matrix)), axis=1)
            corr_matrix = np.corrcoef(returns)

            # 4. Group into clusters based on correlation threshold > 0.7
            clusters = {}
            cluster_counter = 0
            visited = set()

            for i in range(len(valid_symbols)):
                if i in visited:
                    continue

                # Create new cluster
                cluster_id = cluster_counter
                clusters[cluster_id] = [valid_symbols[i]]
                visited.add(i)

                # Check correlations with others
                for j in range(i + 1, len(valid_symbols)):
                    if j not in visited and corr_matrix[i, j] > 0.7:
                        clusters[cluster_id].append(valid_symbols[j])
                        visited.add(j)

                cluster_counter += 1

            # 5. Update database cluster IDs
            for cluster_id, sym_list in clusters.items():
                await db_session.execute(
                    update(AssetRegistry)
                    .where(AssetRegistry.symbol.in_(sym_list))
                    .values(cluster_id=cluster_id, updated_at=datetime.utcnow())
                )
            await db_session.commit()
            logger.info("Clustering completed successfully", total_clusters=cluster_counter)

        except Exception as e:
            logger.error("Failed to recalculate asset clusters", error=str(e))
            await db_session.rollback()
            raise

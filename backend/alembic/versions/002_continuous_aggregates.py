"""create continuous aggregates (non-transactional)

Revision ID: 002_continuous_aggregates
Revises: 001_initial_schema
Create Date: 2026-06-30 12:00:00.000000

"""
from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = '002_continuous_aggregates'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # TimescaleDB continuous aggregates require running outside a transaction.
    # Commit current Alembic transaction, run DDL, then re-open.
    op.execute(text("COMMIT"))
    op.execute(text("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS asset_daily_aggregates
        WITH (timescaledb.continuous) AS
        SELECT
            time_bucket('1 day', time) AS day,
            symbol,
            AVG(zf_score) AS avg_zf_score,
            MAX(zf_score) AS max_zf_score,
            AVG(psi_total) AS avg_psi_total,
            FIRST(price, time) AS open_price,
            LAST(price, time) AS close_price,
            MAX(price) AS high_price,
            MIN(price) AS low_price,
            AVG(volume_24h) AS avg_volume
        FROM asset_snapshots
        GROUP BY day, symbol
    """))
    op.execute(text("BEGIN"))


def downgrade() -> None:
    op.execute(text("COMMIT"))
    op.execute(text("DROP MATERIALIZED VIEW IF EXISTS asset_daily_aggregates"))
    op.execute(text("BEGIN"))

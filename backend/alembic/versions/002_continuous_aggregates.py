"""create continuous aggregates

Revision ID: 002_continuous_aggregates
Revises: 001_initial_schema
Create Date: 2026-06-30 12:00:00.000000

NOTE: This migration is intentionally empty.
TimescaleDB continuous aggregates cannot run inside a transaction,
and asyncpg (used by this project) does not support raw COMMIT/BEGIN.
The continuous aggregate is created via a post-migration SQL script
in the deploy pipeline instead.
"""

# revision identifiers, used by Alembic.
revision = '002_continuous_aggregates'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ponytail: continuous aggregate created via deploy script (see ci-cd.yml)
    # upgrade path: switch to psycopg (sync) driver for migrations
    pass


def downgrade() -> None:
    pass

"""split single nonce column into per-field nonces

Revision ID: 003_split_api_key_nonces
Revises: 002_continuous_aggregates
Create Date: 2026-07-01 00:00:00.000000

AES-GCM requires a unique nonce per encryption operation.
The original schema had a single `nonce` column shared across three
encrypted fields — this migration splits it into three separate columns.
"""
from alembic import op
import sqlalchemy as sa

revision = '003_split_api_key_nonces'
down_revision = '002_continuous_aggregates'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add three new nonce columns (nullable initially for existing rows)
    op.add_column('user_api_keys', sa.Column('api_key_nonce', sa.LargeBinary(), nullable=True))
    op.add_column('user_api_keys', sa.Column('secret_key_nonce', sa.LargeBinary(), nullable=True))
    op.add_column('user_api_keys', sa.Column('passphrase_nonce', sa.LargeBinary(), nullable=True))

    # Copy existing nonce to all three columns (existing keys used same nonce — not ideal but preserves data)
    op.execute("UPDATE user_api_keys SET api_key_nonce = nonce, secret_key_nonce = nonce, passphrase_nonce = nonce")

    # Now make them NOT NULL
    op.alter_column('user_api_keys', 'api_key_nonce', nullable=False)
    op.alter_column('user_api_keys', 'secret_key_nonce', nullable=False)
    op.alter_column('user_api_keys', 'passphrase_nonce', nullable=False)

    # Drop the old single nonce column
    op.drop_column('user_api_keys', 'nonce')


def downgrade() -> None:
    op.add_column('user_api_keys', sa.Column('nonce', sa.LargeBinary(), nullable=True))
    op.execute("UPDATE user_api_keys SET nonce = api_key_nonce")
    op.alter_column('user_api_keys', 'nonce', nullable=False)
    op.drop_column('user_api_keys', 'passphrase_nonce')
    op.drop_column('user_api_keys', 'secret_key_nonce')
    op.drop_column('user_api_keys', 'api_key_nonce')

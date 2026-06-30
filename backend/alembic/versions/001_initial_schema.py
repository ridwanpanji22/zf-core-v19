"""initial schema

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-06-28 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. users Table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('google_id', sa.String(length=255), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('display_name', sa.String(length=255), nullable=True),
        sa.Column('avatar_url', sa.String(length=1000), nullable=True),
        sa.Column('role', sa.String(length=20), server_default='architect', nullable=False),
        sa.Column('status', sa.String(length=20), server_default='active', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('google_id'),
        sa.UniqueConstraint('email')
    )
    op.create_index('idx_users_email', 'users', ['email'], unique=True)
    op.create_index('idx_users_role', 'users', ['role'], unique=False)

    # 2. asset_registry Table
    op.create_table(
        'asset_registry',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('symbol', sa.String(length=50), nullable=False),
        sa.Column('base_currency', sa.String(length=20), nullable=False),
        sa.Column('inst_type', sa.String(length=10), server_default='SWAP', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('cluster_id', sa.Integer(), nullable=True),
        sa.Column('dampening_factor', sa.Float(), server_default='1.0', nullable=False),
        sa.Column('dampening_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('symbol')
    )
    op.create_index('idx_asset_registry_symbol', 'asset_registry', ['symbol'], unique=True)

    # 3. asset_snapshots Table (TimescaleDB target)
    op.create_table(
        'asset_snapshots',
        sa.Column('time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('symbol', sa.String(length=50), nullable=False),
        sa.Column('price', sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column('zf_score', sa.Float(), nullable=False),
        sa.Column('psi_total', sa.Float(), nullable=False),
        sa.Column('d_res', sa.Float(), nullable=False),
        sa.Column('oi', sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column('funding_rate', sa.Float(), nullable=True),
        sa.Column('volume_24h', sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column('bid_depth_ratio', sa.Float(), nullable=True),
        sa.Column('ofi', sa.Float(), nullable=True),
        sa.Column('mode', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('predicted_change_pct', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('time', 'symbol')
    )

    # 4. prediction_log Table (TimescaleDB target)
    op.create_table(
        'prediction_log',
        sa.Column('time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('symbol', sa.String(length=50), nullable=False),
        sa.Column('prediction_type', sa.String(length=30), nullable=False),
        sa.Column('predicted_value', sa.Float(), nullable=False),
        sa.Column('actual_value', sa.Float(), nullable=True),
        sa.Column('error', sa.Float(), nullable=True),
        sa.Column('omega_w1', sa.Float(), nullable=False),
        sa.Column('omega_w2', sa.Float(), nullable=False),
        sa.Column('omega_w3', sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint('time', 'symbol')
    )

    # 5. calibration_log Table
    op.create_table(
        'calibration_log',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('calibrated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('omega_w1_old', sa.Float(), nullable=False),
        sa.Column('omega_w2_old', sa.Float(), nullable=False),
        sa.Column('omega_w3_old', sa.Float(), nullable=False),
        sa.Column('omega_w1_new', sa.Float(), nullable=False),
        sa.Column('omega_w2_new', sa.Float(), nullable=False),
        sa.Column('omega_w3_new', sa.Float(), nullable=False),
        sa.Column('avg_error_before', sa.Float(), nullable=True),
        sa.Column('avg_error_after', sa.Float(), nullable=True),
        sa.Column('samples_used', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # 6. code_red_tracker Table
    op.create_table(
        'code_red_tracker',
        sa.Column('symbol', sa.String(length=50), nullable=False),
        sa.Column('consecutive_sessions', sa.Integer(), server_default='0', nullable=False),
        sa.Column('first_triggered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_triggered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='false', nullable=False),
        sa.PrimaryKeyConstraint('symbol')
    )

    # 7. session_journals Table
    op.create_table(
        'session_journals',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('avg_zf_score', sa.Float(), nullable=True),
        sa.Column('code_red_count', sa.Integer(), nullable=True),
        sa.Column('alerts_sent', sa.Integer(), nullable=True),
        sa.Column('errors_count', sa.Integer(), nullable=True),
        sa.Column('omega_changes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # 8. system_events Table (TimescaleDB target)
    op.create_table(
        'system_events',
        sa.Column('time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('symbol', sa.String(length=50), nullable=True),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('time')
    )

    # 9. user_api_keys Table
    op.create_table(
        'user_api_keys',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('label', sa.String(length=100), nullable=True),
        sa.Column('api_key_encrypted', sa.LargeBinary(), nullable=False),
        sa.Column('secret_key_encrypted', sa.LargeBinary(), nullable=False),
        sa.Column('passphrase_encrypted', sa.LargeBinary(), nullable=False),
        sa.Column('nonce', sa.LargeBinary(), nullable=False),
        sa.Column('api_key_last4', sa.String(length=4), nullable=False),
        sa.Column('permission_level', sa.String(length=20), nullable=True),
        sa.Column('is_valid', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_tested_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_api_keys_user', 'user_api_keys', ['user_id'], unique=False)

    # 10. demo_wallets Table
    op.create_table(
        'demo_wallets',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('balance', sa.Numeric(precision=20, scale=2), server_default='10000.00', nullable=False),
        sa.Column('initial_balance', sa.Numeric(precision=20, scale=2), server_default='10000.00', nullable=False),
        sa.Column('total_pnl', sa.Numeric(precision=20, scale=2), server_default='0.00', nullable=False),
        sa.Column('total_trades', sa.Integer(), server_default='0', nullable=False),
        sa.Column('win_trades', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_reset_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )

    # 11. demo_positions Table
    op.create_table(
        'demo_positions',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(length=50), nullable=False),
        sa.Column('side', sa.String(length=10), nullable=False),
        sa.Column('size_usdt', sa.Numeric(precision=20, scale=2), nullable=False),
        sa.Column('leverage', sa.Integer(), server_default='1', nullable=False),
        sa.Column('entry_price', sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column('exit_price', sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column('margin', sa.Numeric(precision=20, scale=2), nullable=False),
        sa.Column('pnl', sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column('fee', sa.Numeric(precision=20, scale=4), nullable=True),
        sa.Column('status', sa.String(length=20), server_default='open', nullable=False),
        sa.Column('close_reason', sa.String(length=20), nullable=True),
        sa.Column('opened_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_demo_pos_user', 'demo_positions', ['user_id', 'status'], unique=False)
    op.create_index('idx_demo_pos_symbol', 'demo_positions', ['symbol', 'status'], unique=False)

    # 12. system_config Table
    op.create_table(
        'system_config',
        sa.Column('key', sa.String(length=100), nullable=False),
        sa.Column('value', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('key')
    )

    # ==========================================
    # TimescaleDB Raw SQL Extensions & HyperTables
    # ==========================================
    # 1. Create hypertables
    op.execute("SELECT create_hypertable('asset_snapshots', 'time');")
    op.execute("SELECT create_hypertable('prediction_log', 'time');")
    op.execute("SELECT create_hypertable('system_events', 'time');")

    # 2. Add retention policies
    op.execute("SELECT add_retention_policy('asset_snapshots', INTERVAL '30 days');")
    op.execute("SELECT add_retention_policy('prediction_log', INTERVAL '90 days');")
    op.execute("SELECT add_retention_policy('system_events', INTERVAL '90 days');")

    # 3. Continuous aggregates are created in a separate migration (002)
    #    because TimescaleDB requires CREATE MATERIALIZED VIEW ... WITH DATA
    #    to run outside a transaction block.

    # 4. Insert default system configuration settings
    op.execute("INSERT INTO system_config (key, value) VALUES ('demo_mode_enabled', '\"true\"'::jsonb);")
    op.execute("INSERT INTO system_config (key, value) VALUES ('demo_initial_balance', '\"10000\"'::jsonb);")
    op.execute("INSERT INTO system_config (key, value) VALUES ('demo_max_leverage', '\"10\"'::jsonb);")


def downgrade() -> None:
    # Continuous aggregate dropped in 002_continuous_aggregates downgrade

    op.drop_table('system_config')
    op.drop_table('demo_positions')
    op.drop_table('demo_wallets')
    op.drop_table('user_api_keys')
    op.drop_table('system_events')
    op.drop_table('session_journals')
    op.drop_table('code_red_tracker')
    op.drop_table('calibration_log')
    op.drop_table('prediction_log')
    op.drop_table('asset_snapshots')
    op.drop_table('asset_registry')
    op.drop_table('users')

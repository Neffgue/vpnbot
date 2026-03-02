"""Initial schema creation

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('telegram_id', sa.BigInteger(), nullable=False),
        sa.Column('username', sa.String(255), nullable=True),
        sa.Column('first_name', sa.String(255), nullable=True),
        sa.Column('referral_code', sa.String(10), nullable=False),
        sa.Column('referred_by', sa.String(36), nullable=True),
        sa.Column('balance', sa.Numeric(12, 2), nullable=False),
        sa.Column('is_banned', sa.Boolean(), nullable=False),
        sa.Column('is_admin', sa.Boolean(), nullable=False),
        sa.Column('free_trial_used', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['referred_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('referral_code'),
        sa.UniqueConstraint('telegram_id'),
    )
    op.create_index('ix_users_referral_code', 'users', ['referral_code'])
    op.create_index('ix_users_telegram_id', 'users', ['telegram_id'])

    # Create servers table
    op.create_table(
        'servers',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('country_emoji', sa.String(10), nullable=False),
        sa.Column('country_name', sa.String(100), nullable=False),
        sa.Column('host', sa.String(255), nullable=False),
        sa.Column('port', sa.Integer(), nullable=False),
        sa.Column('panel_url', sa.String(500), nullable=False),
        sa.Column('panel_username', sa.String(255), nullable=False),
        sa.Column('panel_password', sa.String(255), nullable=False),
        sa.Column('inbound_id', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('bypass_ru_whitelist', sa.Boolean(), nullable=False),
        sa.Column('order_index', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )
    op.create_index('ix_servers_is_active', 'servers', ['is_active'])
    op.create_index('ix_servers_name', 'servers', ['name'])

    # Create subscriptions table
    op.create_table(
        'subscriptions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('plan_name', sa.String(50), nullable=False),
        sa.Column('period_days', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('device_limit', sa.Integer(), nullable=False),
        sa.Column('traffic_gb', sa.Integer(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('xui_client_uuid', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('xui_client_uuid'),
    )
    op.create_index('ix_subscriptions_expires_at', 'subscriptions', ['expires_at'])
    op.create_index('ix_subscriptions_is_active', 'subscriptions', ['is_active'])
    op.create_index('ix_subscriptions_user_id', 'subscriptions', ['user_id'])
    op.create_index('ix_subscriptions_xui_client_uuid', 'subscriptions', ['xui_client_uuid'])

    # Create subscription_server_association table
    op.create_table(
        'subscription_server_association',
        sa.Column('subscription_id', sa.String(36), nullable=False),
        sa.Column('server_id', sa.String(36), nullable=False),
        sa.ForeignKeyConstraint(['server_id'], ['servers.id'], ),
        sa.ForeignKeyConstraint(['subscription_id'], ['subscriptions.id'], ),
        sa.PrimaryKeyConstraint('subscription_id', 'server_id'),
    )

    # Create payments table
    op.create_table(
        'payments',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('provider_payment_id', sa.String(255), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('plan_name', sa.String(50), nullable=False),
        sa.Column('period_days', sa.Integer(), nullable=False),
        sa.Column('device_limit', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('provider_payment_id'),
    )
    op.create_index('ix_payments_provider_payment_id', 'payments', ['provider_payment_id'])
    op.create_index('ix_payments_status', 'payments', ['status'])
    op.create_index('ix_payments_user_id', 'payments', ['user_id'])

    # Create referrals table
    op.create_table(
        'referrals',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('referrer_id', sa.String(36), nullable=False),
        sa.Column('referred_id', sa.String(36), nullable=False),
        sa.Column('bonus_days', sa.Integer(), nullable=False),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['referred_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['referrer_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('referred_id'),
    )
    op.create_index('ix_referrals_referrer_id', 'referrals', ['referrer_id'])
    op.create_index('ix_referrals_referred_id', 'referrals', ['referred_id'])

    # Create plan_prices table
    op.create_table(
        'plan_prices',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('plan_name', sa.String(50), nullable=False),
        sa.Column('period_days', sa.Integer(), nullable=False),
        sa.Column('price_rub', sa.Numeric(12, 2), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('plan_name', 'period_days', name='uq_plan_period'),
    )

    # Create bot_texts table
    op.create_table(
        'bot_texts',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('key', sa.String(255), nullable=False),
        sa.Column('value', sa.String(4000), nullable=False),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key'),
    )
    op.create_index('ix_bot_texts_key', 'bot_texts', ['key'])

    # Create broadcasts table
    op.create_table(
        'broadcasts',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('message', sa.String(4000), nullable=False),
        sa.Column('is_sent', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('broadcasts')
    op.drop_table('bot_texts')
    op.drop_table('plan_prices')
    op.drop_table('referrals')
    op.drop_table('payments')
    op.drop_table('subscription_server_association')
    op.drop_table('subscriptions')
    op.drop_table('servers')
    op.drop_table('users')

"""add price to subscriptions and auto_renewal to users

Revision ID: 005_add_price_and_auto_renewal
Revises: 004_add_auto_renewal
Create Date: 2026-03-03
"""
from alembic import op
import sqlalchemy as sa

revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Добавляем цену подписки (нужна для авто-продления)
    op.add_column(
        'subscriptions',
        sa.Column('price', sa.Float(), nullable=True, server_default='0.0')
    )


def downgrade() -> None:
    op.drop_column('subscriptions', 'price')

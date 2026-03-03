"""add auto_renewal to users

Revision ID: 004_add_auto_renewal
Revises: 003_add_notification_fields_to_subscriptions
Create Date: 2026-03-03
"""
from alembic import op
import sqlalchemy as sa

revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('auto_renewal', sa.Boolean(), nullable=False, server_default='false')
    )


def downgrade() -> None:
    op.drop_column('users', 'auto_renewal')

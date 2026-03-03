"""add name, device_limit, image_url, description, is_active to plan_prices

Revision ID: 006
Revises: 005
Create Date: 2026-03-03
"""
from alembic import op
import sqlalchemy as sa

revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('plan_prices', sa.Column('name', sa.String(100), nullable=True))
    op.add_column('plan_prices', sa.Column('device_limit', sa.Integer(), nullable=True, server_default='1'))
    op.add_column('plan_prices', sa.Column('image_url', sa.String(500), nullable=True))
    op.add_column('plan_prices', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('plan_prices', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'))


def downgrade() -> None:
    op.drop_column('plan_prices', 'is_active')
    op.drop_column('plan_prices', 'description')
    op.drop_column('plan_prices', 'image_url')
    op.drop_column('plan_prices', 'device_limit')
    op.drop_column('plan_prices', 'name')

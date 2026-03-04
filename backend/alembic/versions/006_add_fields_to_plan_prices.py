"""add name, device_limit, image_url, description, is_active, updated_at to plan_prices

Revision ID: 006
Revises: 005
Create Date: 2026-03-03
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def _column_exists(table: str, column: str) -> bool:
    """Check if a column already exists (works for PostgreSQL and SQLite)."""
    conn = op.get_bind()
    dialect = conn.dialect.name
    try:
        if dialect == 'sqlite':
            result = conn.execute(text(f"PRAGMA table_info({table})"))
            rows = result.fetchall()
            return any(row[1] == column for row in rows)
        else:
            # PostgreSQL
            result = conn.execute(text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name=:t AND column_name=:c"
            ), {"t": table, "c": column})
            return result.fetchone() is not None
    except Exception:
        return False


def upgrade() -> None:
    if not _column_exists('plan_prices', 'name'):
        op.add_column('plan_prices', sa.Column('name', sa.String(100), nullable=True))

    if not _column_exists('plan_prices', 'device_limit'):
        op.add_column('plan_prices', sa.Column('device_limit', sa.Integer(), nullable=True, server_default='1'))

    if not _column_exists('plan_prices', 'image_url'):
        op.add_column('plan_prices', sa.Column('image_url', sa.String(500), nullable=True))

    if not _column_exists('plan_prices', 'description'):
        op.add_column('plan_prices', sa.Column('description', sa.Text(), nullable=True))

    if not _column_exists('plan_prices', 'is_active'):
        op.add_column('plan_prices', sa.Column('is_active', sa.Boolean(), nullable=True, server_default=sa.text('true')))

    if not _column_exists('plan_prices', 'updated_at'):
        op.add_column('plan_prices', sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=True,
        ))


def downgrade() -> None:
    for col in ('updated_at', 'is_active', 'description', 'image_url', 'device_limit', 'name'):
        if _column_exists('plan_prices', col):
            op.drop_column('plan_prices', col)

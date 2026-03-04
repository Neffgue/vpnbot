"""fix plan_prices columns - ensure name, device_limit, image_url, description, is_active exist

Revision ID: 007
Revises: 006
Create Date: 2026-03-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = '007'
down_revision = '006'
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
            result = conn.execute(text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name=:t AND column_name=:c"
            ), {"t": table, "c": column})
            return result.fetchone() is not None
    except Exception:
        return False


def upgrade() -> None:
    conn = op.get_bind()

    if not _column_exists('plan_prices', 'name'):
        op.add_column('plan_prices', sa.Column('name', sa.String(100), nullable=True))

    if not _column_exists('plan_prices', 'device_limit'):
        op.add_column('plan_prices', sa.Column('device_limit', sa.Integer(), nullable=True, server_default='1'))

    if not _column_exists('plan_prices', 'image_url'):
        op.add_column('plan_prices', sa.Column('image_url', sa.String(500), nullable=True))

    if not _column_exists('plan_prices', 'description'):
        op.add_column('plan_prices', sa.Column('description', sa.Text(), nullable=True))

    if not _column_exists('plan_prices', 'is_active'):
        op.add_column('plan_prices', sa.Column('is_active', sa.Boolean(), nullable=True, server_default='1'))

    if not _column_exists('plan_prices', 'updated_at'):
        op.add_column('plan_prices', sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=True,
        ))

    # Set default values for existing rows where columns are NULL
    conn.execute(text("UPDATE plan_prices SET is_active = 1 WHERE is_active IS NULL"))
    conn.execute(text("UPDATE plan_prices SET device_limit = 1 WHERE device_limit IS NULL"))


def downgrade() -> None:
    pass

"""Add notification fields to subscriptions table

Revision ID: 003
Revises: 002
Create Date: 2026-03-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('subscriptions', sa.Column('notified_24h', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('subscriptions', sa.Column('notified_12h', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('subscriptions', sa.Column('notified_1h', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('subscriptions', sa.Column('notified_0h', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('subscriptions', sa.Column('notified_3h_after_expiry', sa.Boolean(), nullable=True, server_default='false'))


def downgrade() -> None:
    op.drop_column('subscriptions', 'notified_3h_after_expiry')
    op.drop_column('subscriptions', 'notified_0h')
    op.drop_column('subscriptions', 'notified_1h')
    op.drop_column('subscriptions', 'notified_12h')
    op.drop_column('subscriptions', 'notified_24h')

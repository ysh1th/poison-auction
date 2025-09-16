"""Add close_at to items to match ORM model

Revision ID: 20250916_add_items_close_at
Revises: 20250916_fix_items_desc
Create Date: 2025-09-16
"""

from alembic import op
import sqlalchemy as sa


revision = '20250916_add_items_close_at'
down_revision = '20250916_fix_items_desc'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('items') as batch:
        batch.add_column(sa.Column('close_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('items') as batch:
        try:
            batch.drop_column('close_at')
        except Exception:
            pass



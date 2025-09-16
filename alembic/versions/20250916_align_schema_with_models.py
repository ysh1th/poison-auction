"""Align schema with ORM models: bids table shape, FKs, cleanup

Revision ID: 20250916_align_schema
Revises: 20250916_add_items_close_at
Create Date: 2025-09-16
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision = '20250916_align_schema'
down_revision = '20250916_add_items_close_at'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    # Drop legacy tables if present
    try:
        bind.execute(text("DROP TABLE IF EXISTS auctions CASCADE"))
    except Exception:
        pass
    try:
        bind.execute(text("DROP TABLE IF EXISTS rooms CASCADE"))
    except Exception:
        pass

    # Recreate bids table if it doesn't match expected shape (detect auction_id column)
    cols = bind.execute(text("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name='bids'
    """)).fetchall()
    colnames = {c[0] for c in cols}
    if 'bids' in bind.dialect.get_table_names(bind) and ('auction_id' in colnames or 'item_id' not in colnames or 'amount' not in colnames):
        bind.execute(text("DROP TABLE IF EXISTS bids CASCADE"))

    if 'bids' not in bind.dialect.get_table_names(bind):
        op.create_table(
            'bids',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('item_id', sa.Integer(), sa.ForeignKey('items.id')),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id')),
            sa.Column('amount', sa.Float(), nullable=False),
            sa.Column('max_budget', sa.Float(), nullable=True),
            sa.Column('bid_increment', sa.Float(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
        )
        op.create_unique_constraint('unique_bid', 'bids', ['item_id', 'user_id'])

    # Ensure FKs exist on owned_items (if table exists)
    if 'owned_items' in bind.dialect.get_table_names(bind):
        # Best effort add FKs if missing
        try:
            op.create_foreign_key('owned_items_user_id_fkey', 'owned_items', 'users', ['user_id'], ['id'])
        except Exception:
            pass
        try:
            op.create_foreign_key('owned_items_item_id_fkey', 'owned_items', 'items', ['item_id'], ['id'])
        except Exception:
            pass


def downgrade() -> None:
    # No-op; we don't restore legacy auctions/rooms.
    pass



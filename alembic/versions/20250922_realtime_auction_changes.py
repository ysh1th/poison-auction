"""
realtime auction changes: add balance, scheduling fields, participants table

Revision ID: 20250922_realtime
Revises: None
Create Date: 2025-09-22
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250922_realtime'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # users.balance
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('balance', sa.Float(), nullable=True))
    # items: start_at, end_at, min_start_price, status may already exist as text; ensure columns
    with op.batch_alter_table('items') as batch_op:
        if not has_column('items', 'start_at'):
            batch_op.add_column(sa.Column('start_at', sa.DateTime(), nullable=True))
        if not has_column('items', 'end_at'):
            batch_op.add_column(sa.Column('end_at', sa.DateTime(), nullable=True))
        if not has_column('items', 'min_start_price'):
            batch_op.add_column(sa.Column('min_start_price', sa.Float(), nullable=True))
        # keep existing status column as is
    # auction_participants
    op.create_table(
        'auction_participants',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('item_id', sa.Integer(), sa.ForeignKey('items.id'), index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), index=True),
        sa.Column('joined_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
    )
    op.create_unique_constraint('unique_participant', 'auction_participants', ['item_id', 'user_id'])


def downgrade() -> None:
    op.drop_constraint('unique_participant', 'auction_participants', type_='unique')
    op.drop_table('auction_participants')
    with op.batch_alter_table('items') as batch_op:
        if has_column('items', 'start_at'):
            batch_op.drop_column('start_at')
        if has_column('items', 'end_at'):
            batch_op.drop_column('end_at')
        if has_column('items', 'min_start_price'):
            batch_op.drop_column('min_start_price')
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('balance')

# Helper to check column existence (works with some backends)
from sqlalchemy import inspect
from alembic.runtime.migration import MigrationContext

def has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    insp = inspect(bind)
    cols = [c['name'] for c in insp.get_columns(table_name)]
    return column_name in cols

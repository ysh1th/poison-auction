"""Add rooms, auctions, and poison bids; update items

Revision ID: 20250915_add_r_p_a_b
Revises: 8efa228320eb
Create Date: 2025-09-15 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# Revision identifiers, used by Alembic
revision: str = '20250915_add_r_p_a_b'
down_revision: Union[str, None] = '8efa228320eb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Creates tables for users, items, rooms, auctions, and bids, and updates items schema
def upgrade() -> None:
    # Create users table if not exists
    op.execute(
        text("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email VARCHAR UNIQUE,
            pw_hash VARCHAR,
            role VARCHAR,
            created_at TIMESTAMP DEFAULT now()
        );
        """)
    )
    # Create items table if not exists
    op.execute(
        text("""
        CREATE TABLE IF NOT EXISTS items (
            id SERIAL PRIMARY KEY,
            title VARCHAR,
            description VARCHAR,
            base_price DOUBLE PRECISION,
            status VARCHAR DEFAULT 'open',
            created_at TIMESTAMP DEFAULT now()
        );
        """)
    )
    # Check if 'desc' column exists before renaming
    op.execute(text("COMMIT;"))  # Ensure previous transaction is committed
    result = op.get_bind().execute(
        text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'items' AND column_name = 'desc';
        """)
    )
    if result.fetchone():
        with op.batch_alter_table('items') as batch:
            batch.alter_column('desc', new_column_name='description')

    # Create rooms table (idempotent)
    op.execute(text("COMMIT;"))  # Ensure fresh transaction
    op.execute(
        text("""
        CREATE TABLE IF NOT EXISTS rooms (
            id SERIAL PRIMARY KEY,
            name VARCHAR UNIQUE NOT NULL,
            status VARCHAR NOT NULL DEFAULT 'open',
            created_at TIMESTAMP DEFAULT now()
        );
        """)
    )

    # Adjust items table
    op.execute(text("COMMIT;"))  # Ensure fresh transaction
    try:
        with op.batch_alter_table('items') as batch:
            batch.add_column(sa.Column('room_id', sa.Integer(), nullable=True))
            batch.add_column(sa.Column('image_url', sa.String(), nullable=True))
            batch.alter_column('base_price', existing_type=sa.Float(), nullable=True)
            batch.alter_column('status', server_default='draft')
            batch.drop_column('close_at')
        op.create_foreign_key('items_room_id_fkey', 'items', 'rooms', ['room_id'], ['id'])
    except Exception:
        pass

    # Replace bids table with new auctions and bids tables
    op.execute(text("COMMIT;"))  # Ensure fresh transaction
    op.execute(text("DROP TABLE IF EXISTS bids CASCADE;"))

    op.execute(text("COMMIT;"))  # Ensure fresh transaction
    op.execute(
        text("""
        CREATE TABLE IF NOT EXISTS auctions (
            id SERIAL PRIMARY KEY,
            room_id INTEGER NOT NULL REFERENCES rooms(id),
            item_id INTEGER NOT NULL UNIQUE REFERENCES items(id),
            status VARCHAR NOT NULL DEFAULT 'scheduled',
            open_at TIMESTAMP NULL,
            close_at TIMESTAMP NULL,
            pre_open_seconds INTEGER NOT NULL DEFAULT 30,
            duration_seconds INTEGER NOT NULL DEFAULT 300,
            current_price DOUBLE PRECISION NOT NULL DEFAULT 0,
            current_high_user_id INTEGER NULL REFERENCES users(id),
            current_high_bid_id INTEGER NULL,
            version INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT now()
        );
        """)
    )

    op.execute(text("COMMIT;"))  # Ensure fresh transaction
    op.execute(
        text("""
        CREATE TABLE IF NOT EXISTS bids (
            id SERIAL PRIMARY KEY,
            auction_id INTEGER NOT NULL REFERENCES auctions(id),
            user_id INTEGER NOT NULL REFERENCES users(id),
            poison_budget DOUBLE PRECISION NOT NULL,
            poison_step DOUBLE PRECISION NOT NULL,
            amount_committed DOUBLE PRECISION NOT NULL DEFAULT 0,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT now(),
            updated_at TIMESTAMP DEFAULT now(),
            UNIQUE (auction_id, user_id)
        );
        """)
    )

# Drops bids, auctions, and rooms tables, and reverts items schema changes
def downgrade() -> None:
    op.execute(text("COMMIT;"))  # Ensure fresh transaction
    op.drop_constraint('bids_user_id_fkey', 'bids', type_='foreignkey')
    op.drop_constraint('bids_auction_id_fkey', 'bids', type_='foreignkey')
    op.drop_table('bids')

    op.execute(text("COMMIT;"))  # Ensure fresh transaction
    op.drop_constraint('auctions_item_id_fkey', 'auctions', type_='foreignkey')
    op.drop_constraint('auctions_room_id_fkey', 'auctions', type_='foreignkey')
    op.drop_table('auctions')

    op.execute(text("COMMIT;"))  # Ensure fresh transaction
    op.drop_constraint('items_room_id_fkey', 'items', type_='foreignkey')
    with op.batch_alter_table('items') as batch:
        batch.add_column(sa.Column('close_at', sa.DateTime(), nullable=True))
        batch.drop_column('image_url')
        batch.drop_column('room_id')
        batch.alter_column('status', server_default='open')

    op.execute(text("COMMIT;"))  # Ensure fresh transaction
    op.execute(text("DROP TABLE IF EXISTS rooms;"))
"""add owned_items inventory table

Revision ID: 20250916_add_owned
Revises: 20250916_add_unsplash
Create Date: 2025-09-16
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20250916_add_owned'
down_revision = '20250916_add_unsplash'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'owned_items',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), nullable=False, index=True),
        sa.Column('item_id', sa.Integer(), nullable=False, index=True),
        sa.Column('acquired_at', sa.DateTime(), nullable=True),
        sa.Column('image_url', sa.String(), nullable=True),
        sa.Column('image_thumb_url', sa.String(), nullable=True),
        sa.Column('image_attribution', sa.String(), nullable=True),
        sa.Column('image_attribution_link', sa.String(), nullable=True),
        sa.Column('unsplash_id', sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('owned_items')



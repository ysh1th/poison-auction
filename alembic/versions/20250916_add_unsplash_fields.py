"""add unsplash fields

Revision ID: 20250916_add_unsplash
Revises: 20250915_add_r_p_a_b
Create Date: 2025-09-16
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20250916_add_unsplash'
down_revision = '20250915_add_r_p_a_b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('items', sa.Column('image_url', sa.String(), nullable=True))
    op.add_column('items', sa.Column('image_thumb_url', sa.String(), nullable=True))
    op.add_column('items', sa.Column('image_attribution', sa.String(), nullable=True))
    op.add_column('items', sa.Column('image_attribution_link', sa.String(), nullable=True))
    op.add_column('items', sa.Column('unsplash_id', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('items', 'unsplash_id')
    op.drop_column('items', 'image_attribution_link')
    op.drop_column('items', 'image_attribution')
    op.drop_column('items', 'image_thumb_url')
    op.drop_column('items', 'image_url')



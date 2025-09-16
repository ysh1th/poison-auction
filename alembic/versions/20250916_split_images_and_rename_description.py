"""Split images to separate table and rename desc->description; add items.image_id

Revision ID: 20250916_split_images
Revises: 20250916_align_schema
Create Date: 2025-09-16
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision = '20250916_split_images'
down_revision = '20250916_align_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    # Create images table
    op.create_table(
        'images',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('unsplash_id', sa.String(), unique=True, nullable=True),
        sa.Column('image_url', sa.String(), nullable=True),
        sa.Column('image_thumb_url', sa.String(), nullable=True),
        sa.Column('image_attribution', sa.String(), nullable=True),
        sa.Column('image_attribution_link', sa.String(), nullable=True),
    )
    op.create_index('ix_images_unsplash_id', 'images', ['unsplash_id'], unique=True)

    # Ensure items has description column (idempotent)
    op.execute(text('ALTER TABLE items ADD COLUMN IF NOT EXISTS "description" VARCHAR'))

    # Backfill description from desc if present
    bind.execute(text("COMMIT;"))
    try:
        bind.execute(text("UPDATE items SET description = COALESCE(description, \"desc\") WHERE description IS NULL"))
    except Exception:
        pass

    # Add image_id
    with op.batch_alter_table('items') as batch:
        try:
            batch.add_column(sa.Column('image_id', sa.Integer(), nullable=True))
        except Exception:
            pass
    try:
        op.create_foreign_key('items_image_id_fkey', 'items', 'images', ['image_id'], ['id'])
    except Exception:
        pass

    # Migrate any inline image fields from items into images and set image_id
    # Only if inline columns exist
    cols = {r[0] for r in bind.execute(text("""
        SELECT column_name FROM information_schema.columns WHERE table_name='items'
    """)).fetchall()}
    inline_cols = {'image_url','image_thumb_url','image_attribution','image_attribution_link','unsplash_id'}
    if inline_cols.issubset(cols):
        # Create images for unique (unsplash_id, image_url) pairs
        bind.execute(text("COMMIT;"))
        bind.execute(text(
            """
            INSERT INTO images (unsplash_id, image_url, image_thumb_url, image_attribution, image_attribution_link)
            SELECT DISTINCT unsplash_id, image_url, image_thumb_url, image_attribution, image_attribution_link
            FROM items
            WHERE image_url IS NOT NULL OR unsplash_id IS NOT NULL
            ON CONFLICT (unsplash_id) DO NOTHING;
            """
        ))
        # Set items.image_id by matching on unsplash_id (preferred) or image_url
        bind.execute(text("COMMIT;"))
        bind.execute(text(
            """
            UPDATE items i
            SET image_id = img.id
            FROM images img
            WHERE (
              (i.unsplash_id IS NOT NULL AND img.unsplash_id = i.unsplash_id)
              OR (i.unsplash_id IS NULL AND i.image_url IS NOT NULL AND img.image_url = i.image_url)
            )
            AND i.image_id IS NULL;
            """
        ))

    # Optionally drop inline image columns (keep for now to avoid destructive op). If you want to drop:
    # with op.batch_alter_table('items') as batch:
    #     for col in ['image_url','image_thumb_url','image_attribution','image_attribution_link','unsplash_id']:
    #         try:
    #             batch.drop_column(col)
    #         except Exception:
    #             pass


def downgrade() -> None:
    # Non-destructive: keep images table and items.image_id
    pass



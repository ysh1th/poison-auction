"""Ensure items.desc exists and backfill from description if present

Revision ID: 20250916_fix_items_desc
Revises: 20250916_fix_users_role_varchar
Create Date: 2025-09-16
"""

from alembic import op
from sqlalchemy import text


revision = '20250916_fix_items_desc'
down_revision = '20250916_fix_users_role_varchar'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(text("COMMIT;"))
    # Add desc column if not exists
    bind.execute(text("ALTER TABLE items ADD COLUMN IF NOT EXISTS \"desc\" VARCHAR"))

    # If description exists and desc is NULL, backfill
    bind.execute(text("COMMIT;"))
    bind.execute(text(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='items' AND column_name='description'
            ) THEN
                UPDATE items SET "desc" = description WHERE "desc" IS NULL;
            END IF;
        END$$;
        """
    ))


def downgrade() -> None:
    # Keep desc column; no destructive downgrade
    pass



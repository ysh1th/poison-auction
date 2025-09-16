"""Ensure users.role is VARCHAR with safe default

Revision ID: 20250916_fix_users_role_varchar
Revises: 20250916_add_owned
Create Date: 2025-09-16
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision = '20250916_fix_users_role_varchar'
down_revision = '20250916_add_owned'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    # Drop default if it casts to enum type "role"
    bind.execute(text("COMMIT;"))
    try:
        bind.execute(text("""
            DO $$
            BEGIN
                IF (SELECT column_default FROM information_schema.columns 
                    WHERE table_name='users' AND column_name='role') LIKE '%::role%' THEN
                    ALTER TABLE users ALTER COLUMN role DROP DEFAULT;
                END IF;
            END$$;
        """))
    except Exception:
        pass

    # Change column type to VARCHAR if not already
    bind.execute(text("COMMIT;"))
    bind.execute(text("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='users' AND column_name='role' AND udt_name <> 'varchar'
            ) THEN
                ALTER TABLE users ALTER COLUMN role TYPE VARCHAR USING role::text;
            END IF;
        END$$;
    """))

    # Set safe default
    try:
        bind.execute(text("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'viewer';"))
    except Exception:
        pass


def downgrade() -> None:
    # No-op: keeping role as VARCHAR is fine
    pass



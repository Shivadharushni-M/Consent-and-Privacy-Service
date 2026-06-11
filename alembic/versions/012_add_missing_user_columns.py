"""add_missing_user_columns

Adds the five columns present in the SQLAlchemy User model that were never
included in a prior Alembic migration:
  - external_id
  - tenant_id
  - primary_identifier_type
  - primary_identifier_value
  - deleted_at

Each column is guarded by an information_schema existence check so the
migration is safe to run against a database that already has some or all of
these columns (e.g. a local dev DB bootstrapped directly from the ORM).

Revision ID: 012
Revises: 06cc4d717681
Create Date: 2026-06-11 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = '012'
down_revision = '06cc4d717681'
branch_labels = None
depends_on = None


def _column_exists(conn, table: str, column: str) -> bool:
    result = conn.execute(
        text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = :c"
        ),
        {"t": table, "c": column},
    )
    return result.fetchone() is not None


def upgrade() -> None:
    conn = op.get_bind()

    if not _column_exists(conn, "users", "external_id"):
        op.add_column("users", sa.Column("external_id", sa.String(length=255), nullable=True))
        op.create_index(op.f("ix_users_external_id"), "users", ["external_id"], unique=False)

    if not _column_exists(conn, "users", "tenant_id"):
        op.add_column("users", sa.Column("tenant_id", sa.String(length=255), nullable=True))
        op.create_index(op.f("ix_users_tenant_id"), "users", ["tenant_id"], unique=False)

    if not _column_exists(conn, "users", "primary_identifier_type"):
        op.add_column("users", sa.Column("primary_identifier_type", sa.String(length=50), nullable=True))

    if not _column_exists(conn, "users", "primary_identifier_value"):
        op.add_column("users", sa.Column("primary_identifier_value", sa.String(length=255), nullable=True))

    if not _column_exists(conn, "users", "deleted_at"):
        op.add_column("users", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
        op.create_index(op.f("ix_users_deleted_at"), "users", ["deleted_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_users_deleted_at"), table_name="users")
    op.drop_column("users", "deleted_at")
    op.drop_column("users", "primary_identifier_value")
    op.drop_column("users", "primary_identifier_type")
    op.drop_index(op.f("ix_users_tenant_id"), table_name="users")
    op.drop_column("users", "tenant_id")
    op.drop_index(op.f("ix_users_external_id"), table_name="users")
    op.drop_column("users", "external_id")

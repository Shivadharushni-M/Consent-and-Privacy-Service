"""fix_full_schema_drift

Resolves all schema drift between SQLAlchemy models and Alembic history.

Missing tables added:
  verification_tokens      (models/tokens.py   – VerificationToken)
  retention_rules          (models/retention.py – RetentionRule)
  retention_jobs           (models/retention.py – RetentionJob)

Missing columns added:
  audit_logs:       tenant_id, subject_id, actor_type, actor_id,
                    event_type, event_time
  consent_history:  tenant_id, granted_at, valid_from, valid_until,
                    source, user_agent, ip_address, meta
  subject_requests: tenant_id, verification_token_id, result_location,
                    error_message, requested_by

Missing enum values added:
  region_enum: INDIA, ROW

Note on subject_requests.verification_token (VARCHAR) added by migration 003:
  That column is not in the current model (the model uses verification_token_id,
  a UUID FK). The legacy string column is left untouched – SQLAlchemy ignores
  extra DB columns not mapped on the model.

Revision ID: 013
Revises: 012
Create Date: 2026-06-11 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

revision = '013'
down_revision = '012'
branch_labels = None
depends_on = None


# ── helpers ──────────────────────────────────────────────────────────────────

def _column_exists(conn, table: str, column: str) -> bool:
    return conn.execute(
        text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = :t AND column_name = :c"
        ),
        {"t": table, "c": column},
    ).fetchone() is not None


def _table_exists(conn, table: str) -> bool:
    return conn.execute(
        text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = :t"
        ),
        {"t": table},
    ).fetchone() is not None


def _enum_value_exists(conn, type_name: str, value: str) -> bool:
    return conn.execute(
        text(
            "SELECT 1 FROM pg_enum "
            "WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = :t) "
            "AND enumlabel = :v"
        ),
        {"t": type_name, "v": value},
    ).fetchone() is not None


# ── upgrade ───────────────────────────────────────────────────────────────────

def upgrade() -> None:
    conn = op.get_bind()

    # ── region_enum: INDIA, ROW ───────────────────────────────────────────────
    if not _enum_value_exists(conn, "region_enum", "INDIA"):
        op.execute("ALTER TYPE region_enum ADD VALUE IF NOT EXISTS 'INDIA'")
    if not _enum_value_exists(conn, "region_enum", "ROW"):
        op.execute("ALTER TYPE region_enum ADD VALUE IF NOT EXISTS 'ROW'")

    # ── verification_tokens (must exist before subject_requests FK) ───────────
    if not _table_exists(conn, "verification_tokens"):
        op.create_table(
            "verification_tokens",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("token", sa.String(length=500), nullable=False),
            sa.Column("purpose", sa.String(length=50), nullable=False),
            sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("tenant_id", sa.String(length=255), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["subject_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        # token: unique=True, index=True in model → single unique index
        op.create_index(
            op.f("ix_verification_tokens_token"),
            "verification_tokens", ["token"], unique=True,
        )
        op.create_index(
            op.f("ix_verification_tokens_purpose"),
            "verification_tokens", ["purpose"], unique=False,
        )
        op.create_index(
            op.f("ix_verification_tokens_subject_id"),
            "verification_tokens", ["subject_id"], unique=False,
        )
        op.create_index(
            op.f("ix_verification_tokens_tenant_id"),
            "verification_tokens", ["tenant_id"], unique=False,
        )
        op.create_index(
            op.f("ix_verification_tokens_expires_at"),
            "verification_tokens", ["expires_at"], unique=False,
        )
        # __table_args__ composite index
        op.create_index(
            "idx_token_subject_purpose",
            "verification_tokens", ["subject_id", "purpose"], unique=False,
        )

    # ── retention_rules ───────────────────────────────────────────────────────
    if not _table_exists(conn, "retention_rules"):
        op.create_table(
            "retention_rules",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("tenant_id", sa.String(length=255), nullable=True),
            sa.Column("entity_type", sa.String(length=50), nullable=False),
            sa.Column("retention_period_days", sa.Integer(), nullable=False),
            sa.Column("applies_to_region", sa.String(length=10), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_retention_rules_tenant_id"),
            "retention_rules", ["tenant_id"], unique=False,
        )
        op.create_index(
            op.f("ix_retention_rules_entity_type"),
            "retention_rules", ["entity_type"], unique=False,
        )
        op.create_index(
            op.f("ix_retention_rules_applies_to_region"),
            "retention_rules", ["applies_to_region"], unique=False,
        )
        # __table_args__ composite index
        op.create_index(
            "idx_retention_rule_entity",
            "retention_rules", ["entity_type", "applies_to_region"], unique=False,
        )

    # ── retention_jobs ────────────────────────────────────────────────────────
    if not _table_exists(conn, "retention_jobs"):
        op.create_table(
            "retention_jobs",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column(
                "started_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False),
            # default=0 in model is Python-side; server_default ensures SQL-level safety
            sa.Column(
                "deleted_records_count",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("0"),
            ),
            sa.Column("log", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_retention_jobs_started_at"),
            "retention_jobs", ["started_at"], unique=False,
        )
        # __table_args__ composite index
        op.create_index(
            "idx_retention_job_status",
            "retention_jobs", ["status", "started_at"], unique=False,
        )

    # ── audit_logs ────────────────────────────────────────────────────────────
    if not _column_exists(conn, "audit_logs", "tenant_id"):
        op.add_column("audit_logs", sa.Column("tenant_id", sa.String(length=255), nullable=True))
        op.create_index(op.f("ix_audit_logs_tenant_id"), "audit_logs", ["tenant_id"], unique=False)

    if not _column_exists(conn, "audit_logs", "subject_id"):
        op.add_column("audit_logs", sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=True))
        op.create_foreign_key(
            "fk_audit_logs_subject_id",
            "audit_logs", "users",
            ["subject_id"], ["id"],
            ondelete="CASCADE",
        )
        op.create_index(op.f("ix_audit_logs_subject_id"), "audit_logs", ["subject_id"], unique=False)

    if not _column_exists(conn, "audit_logs", "actor_type"):
        op.add_column("audit_logs", sa.Column("actor_type", sa.String(length=20), nullable=True))
        op.create_index(op.f("ix_audit_logs_actor_type"), "audit_logs", ["actor_type"], unique=False)

    if not _column_exists(conn, "audit_logs", "actor_id"):
        op.add_column("audit_logs", sa.Column("actor_id", sa.String(length=255), nullable=True))

    if not _column_exists(conn, "audit_logs", "event_type"):
        op.add_column("audit_logs", sa.Column("event_type", sa.String(length=50), nullable=True))
        op.create_index(op.f("ix_audit_logs_event_type"), "audit_logs", ["event_type"], unique=False)

    if not _column_exists(conn, "audit_logs", "event_time"):
        # NOT NULL: server_default fills existing rows with the migration timestamp
        op.add_column(
            "audit_logs",
            sa.Column(
                "event_time",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
        )
        op.create_index(op.f("ix_audit_logs_event_time"), "audit_logs", ["event_time"], unique=False)

    # ── consent_history ───────────────────────────────────────────────────────
    if not _column_exists(conn, "consent_history", "tenant_id"):
        op.add_column("consent_history", sa.Column("tenant_id", sa.String(length=255), nullable=True))
        op.create_index(op.f("ix_consent_history_tenant_id"), "consent_history", ["tenant_id"], unique=False)

    if not _column_exists(conn, "consent_history", "granted_at"):
        op.add_column("consent_history", sa.Column("granted_at", sa.DateTime(timezone=True), nullable=True))

    if not _column_exists(conn, "consent_history", "valid_from"):
        # NOT NULL: server_default fills existing rows with the migration timestamp
        op.add_column(
            "consent_history",
            sa.Column(
                "valid_from",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
        )
        op.create_index(op.f("ix_consent_history_valid_from"), "consent_history", ["valid_from"], unique=False)

    if not _column_exists(conn, "consent_history", "valid_until"):
        op.add_column("consent_history", sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True))
        op.create_index(op.f("ix_consent_history_valid_until"), "consent_history", ["valid_until"], unique=False)

    if not _column_exists(conn, "consent_history", "source"):
        op.add_column("consent_history", sa.Column("source", sa.String(length=50), nullable=True))

    if not _column_exists(conn, "consent_history", "user_agent"):
        op.add_column("consent_history", sa.Column("user_agent", sa.String(length=500), nullable=True))

    if not _column_exists(conn, "consent_history", "ip_address"):
        op.add_column("consent_history", sa.Column("ip_address", sa.String(length=45), nullable=True))

    if not _column_exists(conn, "consent_history", "meta"):
        op.add_column(
            "consent_history",
            sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        )

    # ── subject_requests ──────────────────────────────────────────────────────
    if not _column_exists(conn, "subject_requests", "tenant_id"):
        op.add_column("subject_requests", sa.Column("tenant_id", sa.String(length=255), nullable=True))
        op.create_index(op.f("ix_subject_requests_tenant_id"), "subject_requests", ["tenant_id"], unique=False)

    if not _column_exists(conn, "subject_requests", "verification_token_id"):
        op.add_column("subject_requests", sa.Column("verification_token_id", postgresql.UUID(as_uuid=True), nullable=True))
        op.create_foreign_key(
            "fk_subject_requests_verification_token_id",
            "subject_requests", "verification_tokens",
            ["verification_token_id"], ["id"],
        )
        op.create_index(
            op.f("ix_subject_requests_verification_token_id"),
            "subject_requests", ["verification_token_id"], unique=False,
        )

    if not _column_exists(conn, "subject_requests", "result_location"):
        op.add_column("subject_requests", sa.Column("result_location", sa.String(length=500), nullable=True))

    if not _column_exists(conn, "subject_requests", "error_message"):
        op.add_column("subject_requests", sa.Column("error_message", sa.String(length=1000), nullable=True))

    if not _column_exists(conn, "subject_requests", "requested_by"):
        op.add_column("subject_requests", sa.Column("requested_by", sa.String(length=50), nullable=True))


# ── downgrade ─────────────────────────────────────────────────────────────────

def downgrade() -> None:
    # subject_requests
    op.drop_column("subject_requests", "requested_by")
    op.drop_column("subject_requests", "error_message")
    op.drop_column("subject_requests", "result_location")
    op.drop_index(op.f("ix_subject_requests_verification_token_id"), table_name="subject_requests")
    op.drop_constraint("fk_subject_requests_verification_token_id", "subject_requests", type_="foreignkey")
    op.drop_column("subject_requests", "verification_token_id")
    op.drop_index(op.f("ix_subject_requests_tenant_id"), table_name="subject_requests")
    op.drop_column("subject_requests", "tenant_id")

    # consent_history
    op.drop_column("consent_history", "meta")
    op.drop_column("consent_history", "ip_address")
    op.drop_column("consent_history", "user_agent")
    op.drop_column("consent_history", "source")
    op.drop_index(op.f("ix_consent_history_valid_until"), table_name="consent_history")
    op.drop_column("consent_history", "valid_until")
    op.drop_index(op.f("ix_consent_history_valid_from"), table_name="consent_history")
    op.drop_column("consent_history", "valid_from")
    op.drop_column("consent_history", "granted_at")
    op.drop_index(op.f("ix_consent_history_tenant_id"), table_name="consent_history")
    op.drop_column("consent_history", "tenant_id")

    # audit_logs
    op.drop_index(op.f("ix_audit_logs_event_time"), table_name="audit_logs")
    op.drop_column("audit_logs", "event_time")
    op.drop_index(op.f("ix_audit_logs_event_type"), table_name="audit_logs")
    op.drop_column("audit_logs", "event_type")
    op.drop_column("audit_logs", "actor_id")
    op.drop_index(op.f("ix_audit_logs_actor_type"), table_name="audit_logs")
    op.drop_column("audit_logs", "actor_type")
    op.drop_index(op.f("ix_audit_logs_subject_id"), table_name="audit_logs")
    op.drop_constraint("fk_audit_logs_subject_id", "audit_logs", type_="foreignkey")
    op.drop_column("audit_logs", "subject_id")
    op.drop_index(op.f("ix_audit_logs_tenant_id"), table_name="audit_logs")
    op.drop_column("audit_logs", "tenant_id")

    # tables (drop FK-dependent table last)
    op.drop_index("idx_retention_job_status", table_name="retention_jobs")
    op.drop_index(op.f("ix_retention_jobs_started_at"), table_name="retention_jobs")
    op.drop_table("retention_jobs")

    op.drop_index("idx_retention_rule_entity", table_name="retention_rules")
    op.drop_index(op.f("ix_retention_rules_applies_to_region"), table_name="retention_rules")
    op.drop_index(op.f("ix_retention_rules_entity_type"), table_name="retention_rules")
    op.drop_index(op.f("ix_retention_rules_tenant_id"), table_name="retention_rules")
    op.drop_table("retention_rules")

    op.drop_index("idx_token_subject_purpose", table_name="verification_tokens")
    op.drop_index(op.f("ix_verification_tokens_expires_at"), table_name="verification_tokens")
    op.drop_index(op.f("ix_verification_tokens_tenant_id"), table_name="verification_tokens")
    op.drop_index(op.f("ix_verification_tokens_subject_id"), table_name="verification_tokens")
    op.drop_index(op.f("ix_verification_tokens_purpose"), table_name="verification_tokens")
    op.drop_index(op.f("ix_verification_tokens_token"), table_name="verification_tokens")
    op.drop_table("verification_tokens")

    # PostgreSQL does not support removing enum values — region_enum values
    # 'INDIA' and 'ROW' cannot be reverted in downgrade.

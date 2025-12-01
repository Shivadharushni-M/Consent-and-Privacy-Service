"""add specification models and fields

Revision ID: 005
Revises: 004
Create Date: 2025-01-21 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from sqlalchemy import text
    from sqlalchemy.exc import InternalError, OperationalError
    
    conn = op.get_bind()
    
    # Helper function to execute SQL with transaction error handling
    def execute_safe(query, params=None):
        """Execute SQL query with automatic error handling for transaction errors"""
        try:
            return conn.execute(text(query), params or {})
        except (InternalError, OperationalError) as e:
            # If transaction is aborted, we can't execute queries
            # This should not happen if we check existence before operations
            if "current transaction is aborted" in str(e).lower():
                # Re-raise to be caught by the calling function
                raise
            raise
    
    # Helper function to check if column exists
    def column_exists(table_name: str, column_name: str) -> bool:
        try:
            result = execute_safe("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = :table_name AND column_name = :column_name
            """, {"table_name": table_name, "column_name": column_name})
            return result.fetchone() is not None
        except Exception:
            return False
    
    # Helper function to check if table exists
    def table_exists(table_name: str) -> bool:
        try:
            result = execute_safe("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_name = :table_name
                )
            """, {"table_name": table_name})
            return result.scalar()
        except Exception:
            return False
    
    # Helper function to check if index exists
    def index_exists(index_name: str, table_name: str = None) -> bool:
        try:
            if table_name:
                result = execute_safe("""
                    SELECT EXISTS (
                        SELECT 1 FROM pg_indexes 
                        WHERE indexname = :index_name AND tablename = :table_name
                    )
                """, {"index_name": index_name, "table_name": table_name})
            else:
                result = execute_safe("""
                    SELECT EXISTS (
                        SELECT 1 FROM pg_indexes 
                        WHERE indexname = :index_name
                    )
                """, {"index_name": index_name})
            return result.scalar()
        except Exception:
            return False
    
    # Helper function to check if foreign key exists
    def foreign_key_exists(fk_name: str, table_name: str = None) -> bool:
        try:
            if table_name:
                result = execute_safe("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.table_constraints 
                        WHERE constraint_name = :fk_name 
                        AND table_name = :table_name 
                        AND constraint_type = 'FOREIGN KEY'
                    )
                """, {"fk_name": fk_name, "table_name": table_name})
            else:
                result = execute_safe("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.table_constraints 
                        WHERE constraint_name = :fk_name 
                        AND constraint_type = 'FOREIGN KEY'
                    )
                """, {"fk_name": fk_name})
            return result.scalar()
        except Exception:
            return False
    
    # Add new columns to users table
    if not column_exists("users", "external_id"):
        op.add_column("users", sa.Column("external_id", sa.String(255), nullable=True))
    if not column_exists("users", "tenant_id"):
        op.add_column("users", sa.Column("tenant_id", sa.String(255), nullable=True))
    if not column_exists("users", "primary_identifier_type"):
        op.add_column("users", sa.Column("primary_identifier_type", sa.String(50), nullable=True))
    if not column_exists("users", "primary_identifier_value"):
        op.add_column("users", sa.Column("primary_identifier_value", sa.String(255), nullable=True))
    if not column_exists("users", "deleted_at"):
        op.add_column("users", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    
    # Create indexes only if they don't exist
    if not index_exists("ix_users_external_id", "users"):
        op.create_index("ix_users_external_id", "users", ["external_id"], unique=False)
    if not index_exists("ix_users_tenant_id", "users"):
        op.create_index("ix_users_tenant_id", "users", ["tenant_id"], unique=False)
    if not index_exists("ix_users_deleted_at", "users"):
        op.create_index("ix_users_deleted_at", "users", ["deleted_at"], unique=False)

    # Add new columns to consent_history table
    if not column_exists("consent_history", "tenant_id"):
        op.add_column("consent_history", sa.Column("tenant_id", sa.String(255), nullable=True))
    if not column_exists("consent_history", "vendor_id"):
        op.add_column("consent_history", sa.Column("vendor_id", postgresql.UUID(as_uuid=True), nullable=True))
    if not column_exists("consent_history", "legal_basis"):
        op.add_column("consent_history", sa.Column("legal_basis", sa.String(50), nullable=True))
    if not column_exists("consent_history", "granted_at"):
        op.add_column("consent_history", sa.Column("granted_at", sa.DateTime(timezone=True), nullable=True))
    if not column_exists("consent_history", "valid_from"):
        op.add_column("consent_history", sa.Column("valid_from", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False))
    if not column_exists("consent_history", "valid_until"):
        op.add_column("consent_history", sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True))
    if not column_exists("consent_history", "policy_version_id"):
        op.add_column("consent_history", sa.Column("policy_version_id", postgresql.UUID(as_uuid=True), nullable=True))
    if not column_exists("consent_history", "source"):
        op.add_column("consent_history", sa.Column("source", sa.String(50), nullable=True))
    if not column_exists("consent_history", "user_agent"):
        op.add_column("consent_history", sa.Column("user_agent", sa.String(500), nullable=True))
    if not column_exists("consent_history", "ip_address"):
        op.add_column("consent_history", sa.Column("ip_address", sa.String(45), nullable=True))
    if not column_exists("consent_history", "meta"):
        op.add_column("consent_history", sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    # Create indexes only if they don't exist
    if not index_exists("ix_consent_history_tenant_id", "consent_history"):
        op.create_index("ix_consent_history_tenant_id", "consent_history", ["tenant_id"], unique=False)
    if not index_exists("ix_consent_history_vendor_id", "consent_history"):
        op.create_index("ix_consent_history_vendor_id", "consent_history", ["vendor_id"], unique=False)
    if not index_exists("ix_consent_history_legal_basis", "consent_history"):
        op.create_index("ix_consent_history_legal_basis", "consent_history", ["legal_basis"], unique=False)
    if not index_exists("ix_consent_history_valid_from", "consent_history"):
        op.create_index("ix_consent_history_valid_from", "consent_history", ["valid_from"], unique=False)
    if not index_exists("ix_consent_history_valid_until", "consent_history"):
        op.create_index("ix_consent_history_valid_until", "consent_history", ["valid_until"], unique=False)
    if not index_exists("ix_consent_history_policy_version_id", "consent_history"):
        op.create_index("ix_consent_history_policy_version_id", "consent_history", ["policy_version_id"], unique=False)

    # Add new columns to audit_logs table
    if not column_exists("audit_logs", "tenant_id"):
        op.add_column("audit_logs", sa.Column("tenant_id", sa.String(255), nullable=True))
    if not column_exists("audit_logs", "subject_id"):
        op.add_column("audit_logs", sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=True))
    if not column_exists("audit_logs", "actor_type"):
        op.add_column("audit_logs", sa.Column("actor_type", sa.String(20), nullable=True))
    if not column_exists("audit_logs", "actor_id"):
        op.add_column("audit_logs", sa.Column("actor_id", sa.String(255), nullable=True))
    if not column_exists("audit_logs", "event_type"):
        op.add_column("audit_logs", sa.Column("event_type", sa.String(50), nullable=True))
    if not column_exists("audit_logs", "event_time"):
        op.add_column("audit_logs", sa.Column("event_time", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False))
    
    # Create indexes and foreign keys only if they don't exist
    if not index_exists("ix_audit_logs_tenant_id", "audit_logs"):
        op.create_index("ix_audit_logs_tenant_id", "audit_logs", ["tenant_id"], unique=False)
    if not index_exists("ix_audit_logs_subject_id", "audit_logs"):
        op.create_index("ix_audit_logs_subject_id", "audit_logs", ["subject_id"], unique=False)
    if not index_exists("ix_audit_logs_actor_type", "audit_logs"):
        op.create_index("ix_audit_logs_actor_type", "audit_logs", ["actor_type"], unique=False)
    if not index_exists("ix_audit_logs_event_type", "audit_logs"):
        op.create_index("ix_audit_logs_event_type", "audit_logs", ["event_type"], unique=False)
    if not index_exists("ix_audit_logs_event_time", "audit_logs"):
        op.create_index("ix_audit_logs_event_time", "audit_logs", ["event_time"], unique=False)
    if not foreign_key_exists("fk_audit_logs_subject_id", "audit_logs"):
        op.create_foreign_key("fk_audit_logs_subject_id", "audit_logs", "users", ["subject_id"], ["id"], ondelete="CASCADE")

    # Add new columns to subject_requests table
    if not column_exists("subject_requests", "tenant_id"):
        op.add_column("subject_requests", sa.Column("tenant_id", sa.String(255), nullable=True))
    if not column_exists("subject_requests", "verification_token_id"):
        op.add_column("subject_requests", sa.Column("verification_token_id", postgresql.UUID(as_uuid=True), nullable=True))
    if not column_exists("subject_requests", "result_location"):
        op.add_column("subject_requests", sa.Column("result_location", sa.String(500), nullable=True))
    if not column_exists("subject_requests", "error_message"):
        op.add_column("subject_requests", sa.Column("error_message", sa.String(1000), nullable=True))
    if not column_exists("subject_requests", "requested_by"):
        op.add_column("subject_requests", sa.Column("requested_by", sa.String(50), nullable=True))
    
    # Create indexes only if they don't exist
    if not index_exists("ix_subject_requests_tenant_id", "subject_requests"):
        op.create_index("ix_subject_requests_tenant_id", "subject_requests", ["tenant_id"], unique=False)
    if not index_exists("ix_subject_requests_verification_token_id", "subject_requests"):
        op.create_index("ix_subject_requests_verification_token_id", "subject_requests", ["verification_token_id"], unique=False)

    # Create policies table
    if not table_exists("policies"):
        op.create_table(
            "policies",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("tenant_id", sa.String(255), nullable=True),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("description", sa.String(1000), nullable=True),
            sa.Column("region_code", sa.String(10), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("current_version_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        if not index_exists("ix_policies_tenant_id", "policies"):
            op.create_index("ix_policies_tenant_id", "policies", ["tenant_id"], unique=False)
        if not index_exists("ix_policies_region_code", "policies"):
            op.create_index("ix_policies_region_code", "policies", ["region_code"], unique=False)
        if not index_exists("idx_policy_tenant_region", "policies"):
            op.create_index("idx_policy_tenant_region", "policies", ["tenant_id", "region_code"], unique=False)

    # Create policy_versions table
    if not table_exists("policy_versions"):
        op.create_table(
            "policy_versions",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("policy_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("version_number", sa.Integer(), nullable=False),
            sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
            sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
            sa.Column("matrix", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("created_by", sa.String(255), nullable=True),
            sa.ForeignKeyConstraint(["policy_id"], ["policies.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        if not index_exists("ix_policy_versions_policy_id", "policy_versions"):
            op.create_index("ix_policy_versions_policy_id", "policy_versions", ["policy_id"], unique=False)
        if not index_exists("ix_policy_versions_version_number", "policy_versions"):
            op.create_index("ix_policy_versions_version_number", "policy_versions", ["version_number"], unique=False)
        if not index_exists("ix_policy_versions_effective_from", "policy_versions"):
            op.create_index("ix_policy_versions_effective_from", "policy_versions", ["effective_from"], unique=False)
        if not index_exists("ix_policy_versions_effective_to", "policy_versions"):
            op.create_index("ix_policy_versions_effective_to", "policy_versions", ["effective_to"], unique=False)
        if not index_exists("idx_policy_version", "policy_versions"):
            op.create_index("idx_policy_version", "policy_versions", ["policy_id", "version_number"], unique=True)
        if not index_exists("idx_policy_effective", "policy_versions"):
            op.create_index("idx_policy_effective", "policy_versions", ["policy_id", "effective_from", "effective_to"], unique=False)

    # Create purpose_groups table
    if not table_exists("purpose_groups"):
        op.create_table(
            "purpose_groups",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("tenant_id", sa.String(255), nullable=True),
            sa.Column("code", sa.String(100), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("precedence", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("code"),
        )
        if not index_exists("ix_purpose_groups_tenant_id", "purpose_groups"):
            op.create_index("ix_purpose_groups_tenant_id", "purpose_groups", ["tenant_id"], unique=False)
        if not index_exists("ix_purpose_groups_code", "purpose_groups"):
            op.create_index("ix_purpose_groups_code", "purpose_groups", ["code"], unique=True)
        if not index_exists("idx_purpose_group_tenant_code", "purpose_groups"):
            op.create_index("idx_purpose_group_tenant_code", "purpose_groups", ["tenant_id", "code"], unique=False)

    # Create purposes table
    if not table_exists("purposes"):
        op.create_table(
            "purposes",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("tenant_id", sa.String(255), nullable=True),
            sa.Column("code", sa.String(100), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("purpose_group_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
            sa.ForeignKeyConstraint(["purpose_group_id"], ["purpose_groups.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("code"),
        )
        if not index_exists("ix_purposes_tenant_id", "purposes"):
            op.create_index("ix_purposes_tenant_id", "purposes", ["tenant_id"], unique=False)
        if not index_exists("ix_purposes_code", "purposes"):
            op.create_index("ix_purposes_code", "purposes", ["code"], unique=True)
        if not index_exists("ix_purposes_purpose_group_id", "purposes"):
            op.create_index("ix_purposes_purpose_group_id", "purposes", ["purpose_group_id"], unique=False)
        if not index_exists("idx_purpose_tenant_code", "purposes"):
            op.create_index("idx_purpose_tenant_code", "purposes", ["tenant_id", "code"], unique=False)

    # Create vendors table
    if not table_exists("vendors"):
        op.create_table(
        "vendors",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(255), nullable=True),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("relationship_type", sa.String(50), nullable=True),
        sa.Column("dpa_url", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("code"),
        )
        if not index_exists("ix_vendors_tenant_id", "vendors"):
            op.create_index("ix_vendors_tenant_id", "vendors", ["tenant_id"], unique=False)
        if not index_exists("ix_vendors_code", "vendors"):
            op.create_index("ix_vendors_code", "vendors", ["code"], unique=True)
        if not index_exists("idx_vendor_tenant_code", "vendors"):
            op.create_index("idx_vendor_tenant_code", "vendors", ["tenant_id", "code"], unique=False)

    # Create regions table
    if not table_exists("regions"):
        op.create_table(
            "regions",
            sa.Column("code", sa.String(10), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("policy_variant", sa.String(50), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.PrimaryKeyConstraint("code"),
        )

    # Create verification_tokens table
    if not table_exists("verification_tokens"):
        op.create_table(
        "verification_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token", sa.String(500), nullable=False),
        sa.Column("purpose", sa.String(50), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(255), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["subject_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        if not index_exists("ix_verification_tokens_token", "verification_tokens"):
            op.create_index("ix_verification_tokens_token", "verification_tokens", ["token"], unique=True)
        if not index_exists("ix_verification_tokens_purpose", "verification_tokens"):
            op.create_index("ix_verification_tokens_purpose", "verification_tokens", ["purpose"], unique=False)
        if not index_exists("ix_verification_tokens_subject_id", "verification_tokens"):
            op.create_index("ix_verification_tokens_subject_id", "verification_tokens", ["subject_id"], unique=False)
        if not index_exists("ix_verification_tokens_tenant_id", "verification_tokens"):
            op.create_index("ix_verification_tokens_tenant_id", "verification_tokens", ["tenant_id"], unique=False)
        if not index_exists("ix_verification_tokens_expires_at", "verification_tokens"):
            op.create_index("ix_verification_tokens_expires_at", "verification_tokens", ["expires_at"], unique=False)
        if not index_exists("idx_token_subject_purpose", "verification_tokens"):
            op.create_index("idx_token_subject_purpose", "verification_tokens", ["subject_id", "purpose"], unique=False)

    # Create retention_rules table
    if not table_exists("retention_rules"):
        op.create_table(
            "retention_rules",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("tenant_id", sa.String(255), nullable=True),
            sa.Column("entity_type", sa.String(50), nullable=False),
            sa.Column("retention_period_days", sa.Integer(), nullable=False),
            sa.Column("applies_to_region", sa.String(10), nullable=True),
            sa.Column("applies_to_legal_basis", sa.String(50), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        if not index_exists("ix_retention_rules_tenant_id", "retention_rules"):
            op.create_index("ix_retention_rules_tenant_id", "retention_rules", ["tenant_id"], unique=False)
        if not index_exists("ix_retention_rules_entity_type", "retention_rules"):
            op.create_index("ix_retention_rules_entity_type", "retention_rules", ["entity_type"], unique=False)
        if not index_exists("ix_retention_rules_applies_to_region", "retention_rules"):
            op.create_index("ix_retention_rules_applies_to_region", "retention_rules", ["applies_to_region"], unique=False)
        if not index_exists("ix_retention_rules_applies_to_legal_basis", "retention_rules"):
            op.create_index("ix_retention_rules_applies_to_legal_basis", "retention_rules", ["applies_to_legal_basis"], unique=False)
        if not index_exists("idx_retention_rule_entity", "retention_rules"):
            op.create_index("idx_retention_rule_entity", "retention_rules", ["entity_type", "applies_to_region"], unique=False)

    # Create retention_jobs table
    if not table_exists("retention_jobs"):
        op.create_table(
            "retention_jobs",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="running"),
            sa.Column("deleted_records_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("log", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        if not index_exists("ix_retention_jobs_started_at", "retention_jobs"):
            op.create_index("ix_retention_jobs_started_at", "retention_jobs", ["started_at"], unique=False)
        if not index_exists("idx_retention_job_status", "retention_jobs"):
            op.create_index("idx_retention_job_status", "retention_jobs", ["status", "started_at"], unique=False)

    # Add foreign key for verification_token_id in subject_requests
    if not foreign_key_exists("fk_subject_requests_verification_token_id", "subject_requests"):
        op.create_foreign_key(
            "fk_subject_requests_verification_token_id",
            "subject_requests",
            "verification_tokens",
            ["verification_token_id"],
            ["id"],
        )


def downgrade() -> None:
    op.drop_table("idempotency_keys")
    op.drop_constraint("fk_subject_requests_verification_token_id", "subject_requests", type_="foreignkey")
    op.drop_table("retention_jobs")
    op.drop_table("retention_rules")
    op.drop_table("verification_tokens")
    op.drop_table("regions")
    op.drop_table("vendors")
    op.drop_table("purposes")
    op.drop_table("purpose_groups")
    op.drop_table("policy_versions")
    op.drop_table("policies")
    
    op.drop_index("ix_subject_requests_verification_token_id", table_name="subject_requests")
    op.drop_index("ix_subject_requests_tenant_id", table_name="subject_requests")
    op.drop_column("subject_requests", "requested_by")
    op.drop_column("subject_requests", "error_message")
    op.drop_column("subject_requests", "result_location")
    op.drop_column("subject_requests", "verification_token_id")
    op.drop_column("subject_requests", "tenant_id")
    
    op.drop_constraint("fk_audit_logs_subject_id", "audit_logs", type_="foreignkey")
    op.drop_index("ix_audit_logs_event_time", table_name="audit_logs")
    op.drop_index("ix_audit_logs_event_type", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_type", table_name="audit_logs")
    op.drop_index("ix_audit_logs_subject_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_tenant_id", table_name="audit_logs")
    op.drop_column("audit_logs", "event_time")
    op.drop_column("audit_logs", "event_type")
    op.drop_column("audit_logs", "actor_id")
    op.drop_column("audit_logs", "actor_type")
    op.drop_column("audit_logs", "subject_id")
    op.drop_column("audit_logs", "tenant_id")
    
    op.drop_index("ix_consent_history_policy_version_id", table_name="consent_history")
    op.drop_index("ix_consent_history_valid_until", table_name="consent_history")
    op.drop_index("ix_consent_history_valid_from", table_name="consent_history")
    op.drop_index("ix_consent_history_legal_basis", table_name="consent_history")
    op.drop_index("ix_consent_history_vendor_id", table_name="consent_history")
    op.drop_index("ix_consent_history_tenant_id", table_name="consent_history")
    op.drop_column("consent_history", "meta")
    op.drop_column("consent_history", "ip_address")
    op.drop_column("consent_history", "user_agent")
    op.drop_column("consent_history", "source")
    op.drop_column("consent_history", "policy_version_id")
    op.drop_column("consent_history", "valid_until")
    op.drop_column("consent_history", "valid_from")
    op.drop_column("consent_history", "granted_at")
    op.drop_column("consent_history", "legal_basis")
    op.drop_column("consent_history", "vendor_id")
    op.drop_column("consent_history", "tenant_id")
    
    op.drop_index("ix_users_deleted_at", table_name="users")
    op.drop_index("ix_users_tenant_id", table_name="users")
    op.drop_index("ix_users_external_id", table_name="users")
    op.drop_column("users", "deleted_at")
    op.drop_column("users", "primary_identifier_value")
    op.drop_column("users", "primary_identifier_type")
    op.drop_column("users", "tenant_id")
    op.drop_column("users", "external_id")

"""add vendor consents

Revision ID: 004
Revises: 003
Create Date: 2025-01-20 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    vendor_enum = sa.Enum(
        "google",
        "facebook",
        "sendgrid",
        "mailgun",
        "twilio",
        "stripe",
        "aws",
        "azure",
        name="vendor_enum",
        create_type=False,
    )
    # Enum will be created automatically by SQLAlchemy when creating the table

    # Create vendor_consents table
    op.create_table(
        "vendor_consents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vendor", vendor_enum, nullable=False),
        sa.Column(
            "purpose",
            sa.Enum(
                "analytics",
                "ads",
                "email",
                "location",
                "marketing",
                "personalization",
                "data_sharing",
                name="purpose_enum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("status", sa.Enum("granted", "denied", "revoked", name="status_enum", create_type=False), nullable=False),
        sa.Column(
            "region",
            sa.Enum(
                "EU",
                "US",
                "INDIA",
                "ROW",
                "IN",
                "BR",
                "SG",
                "AU",
                "JP",
                "CA",
                "UK",
                "ZA",
                "KR",
                name="region_enum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("policy_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vendor_consents_user_id", "vendor_consents", ["user_id"], unique=False)
    op.create_index("ix_vendor_consents_vendor", "vendor_consents", ["vendor"], unique=False)
    op.create_index("ix_vendor_consents_purpose", "vendor_consents", ["purpose"], unique=False)
    op.create_index("ix_vendor_consents_timestamp", "vendor_consents", ["timestamp"], unique=False)
    op.create_index("ix_vendor_consents_expires_at", "vendor_consents", ["expires_at"], unique=False)
    op.create_index("idx_user_vendor_purpose", "vendor_consents", ["user_id", "vendor", "purpose"], unique=False)
    op.create_index("idx_user_vendor_timestamp", "vendor_consents", ["user_id", "vendor", "timestamp"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_user_vendor_timestamp", table_name="vendor_consents")
    op.drop_index("idx_user_vendor_purpose", table_name="vendor_consents")
    op.drop_index("ix_vendor_consents_expires_at", table_name="vendor_consents")
    op.drop_index("ix_vendor_consents_timestamp", table_name="vendor_consents")
    op.drop_index("ix_vendor_consents_purpose", table_name="vendor_consents")
    op.drop_index("ix_vendor_consents_vendor", table_name="vendor_consents")
    op.drop_index("ix_vendor_consents_user_id", table_name="vendor_consents")
    op.drop_table("vendor_consents")
    bind = op.get_bind()
    vendor_enum = sa.Enum(name="vendor_enum")
    vendor_enum.drop(bind, checkfirst=True)


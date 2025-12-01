"""add vendor consents

Revision ID: 004
Revises: 003
Create Date: 2025-01-20 00:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types using DO blocks (handles errors gracefully without aborting transaction)
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'vendor_enum') THEN
                CREATE TYPE vendor_enum AS ENUM (
                    'google', 'facebook', 'sendgrid', 'mailgun', 
                    'twilio', 'stripe', 'aws', 'azure'
                );
            END IF;
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)
    
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'purpose_enum') THEN
                CREATE TYPE purpose_enum AS ENUM (
                    'analytics', 'ads', 'email', 'location', 
                    'marketing', 'personalization', 'data_sharing'
                );
            END IF;
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)
    
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'status_enum') THEN
                CREATE TYPE status_enum AS ENUM ('granted', 'denied', 'revoked');
            END IF;
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)
    
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'region_enum') THEN
                CREATE TYPE region_enum AS ENUM (
                    'EU', 'US', 'INDIA', 'ROW', 'IN', 'BR', 'SG', 
                    'AU', 'JP', 'CA', 'UK', 'ZA', 'KR'
                );
            END IF;
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)
    
    # Create vendor_consents table using DO block to handle if it already exists
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = 'vendor_consents'
            ) THEN
                CREATE TABLE vendor_consents (
                    id UUID NOT NULL PRIMARY KEY,
                    user_id UUID NOT NULL,
                    vendor vendor_enum NOT NULL,
                    purpose purpose_enum NOT NULL,
                    status status_enum NOT NULL,
                    region region_enum NOT NULL,
                    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
                    expires_at TIMESTAMP WITH TIME ZONE,
                    policy_snapshot JSONB,
                    CONSTRAINT fk_vendor_consents_user_id 
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );
            END IF;
        EXCEPTION WHEN duplicate_table THEN NULL;
        END $$;
    """)
    
    # Create indexes using DO blocks
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_vendor_consents_user_id') THEN
                CREATE INDEX ix_vendor_consents_user_id ON vendor_consents(user_id);
            END IF;
        EXCEPTION WHEN duplicate_table THEN NULL;
        END $$;
    """)
    
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_vendor_consents_vendor') THEN
                CREATE INDEX ix_vendor_consents_vendor ON vendor_consents(vendor);
            END IF;
        EXCEPTION WHEN duplicate_table THEN NULL;
        END $$;
    """)
    
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_vendor_consents_purpose') THEN
                CREATE INDEX ix_vendor_consents_purpose ON vendor_consents(purpose);
            END IF;
        EXCEPTION WHEN duplicate_table THEN NULL;
        END $$;
    """)
    
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_vendor_consents_timestamp') THEN
                CREATE INDEX ix_vendor_consents_timestamp ON vendor_consents(timestamp);
            END IF;
        EXCEPTION WHEN duplicate_table THEN NULL;
        END $$;
    """)
    
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_vendor_consents_expires_at') THEN
                CREATE INDEX ix_vendor_consents_expires_at ON vendor_consents(expires_at);
            END IF;
        EXCEPTION WHEN duplicate_table THEN NULL;
        END $$;
    """)
    
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_user_vendor_purpose') THEN
                CREATE INDEX idx_user_vendor_purpose ON vendor_consents(user_id, vendor, purpose);
            END IF;
        EXCEPTION WHEN duplicate_table THEN NULL;
        END $$;
    """)
    
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_user_vendor_timestamp') THEN
                CREATE INDEX idx_user_vendor_timestamp ON vendor_consents(user_id, vendor, timestamp);
            END IF;
        EXCEPTION WHEN duplicate_table THEN NULL;
        END $$;
    """)
    


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


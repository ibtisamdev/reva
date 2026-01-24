"""Migrate to Better Auth schema.

Revision ID: 002
Revises: 001
Create Date: 2026-01-24 12:00:00.000000

This migration:
1. Creates Better Auth tables (user, session, account, verification, organization, member, invitation)
2. Replaces our organizations/users tables with Better Auth's
3. Creates shop_settings table for Shopify-specific data
4. Updates other tables to use string organization_id (Better Auth uses strings)
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ============================================
    # Drop old tables and their dependencies
    # ============================================

    # Drop foreign key constraints first
    op.drop_constraint("fk_users_organization_id_organizations", "users", type_="foreignkey")
    op.drop_constraint("fk_products_organization_id_organizations", "products", type_="foreignkey")
    op.drop_constraint(
        "fk_knowledge_articles_organization_id_organizations",
        "knowledge_articles",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_conversations_organization_id_organizations", "conversations", type_="foreignkey"
    )

    # Drop vector indexes
    op.execute("DROP INDEX IF EXISTS ix_products_embedding")

    # Drop old indexes
    op.drop_index("ix_users_organization_id", table_name="users")
    op.drop_index("ix_users_clerk_user_id", table_name="users")
    op.drop_index("ix_products_organization_shopify_id", table_name="products")

    # Drop old tables
    op.drop_table("users")
    op.drop_table("organizations")

    # Drop old enum
    op.execute("DROP TYPE IF EXISTS user_role")

    # ============================================
    # Create Better Auth tables
    # ============================================

    # user table (Better Auth core)
    op.create_table(
        "user",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("emailVerified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("image", sa.Text(), nullable=True),
        sa.Column(
            "createdAt", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column(
            "updatedAt", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column("role", sa.String(50), nullable=True, server_default="member"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    # session table (Better Auth core)
    op.create_table(
        "session",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("userId", sa.String(36), nullable=False),
        sa.Column("token", sa.String(255), nullable=False),
        sa.Column("expiresAt", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ipAddress", sa.String(255), nullable=True),
        sa.Column("userAgent", sa.Text(), nullable=True),
        sa.Column(
            "createdAt", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column(
            "updatedAt", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.ForeignKeyConstraint(["userId"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )

    # account table (Better Auth core - OAuth/password)
    op.create_table(
        "account",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("userId", sa.String(36), nullable=False),
        sa.Column("accountId", sa.String(255), nullable=False),
        sa.Column("providerId", sa.String(255), nullable=False),
        sa.Column("accessToken", sa.Text(), nullable=True),
        sa.Column("refreshToken", sa.Text(), nullable=True),
        sa.Column("accessTokenExpiresAt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refreshTokenExpiresAt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scope", sa.Text(), nullable=True),
        sa.Column("idToken", sa.Text(), nullable=True),
        sa.Column("password", sa.Text(), nullable=True),
        sa.Column(
            "createdAt", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column(
            "updatedAt", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.ForeignKeyConstraint(["userId"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # verification table (Better Auth core - email verification, etc.)
    op.create_table(
        "verification",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("identifier", sa.String(255), nullable=False),
        sa.Column("value", sa.String(255), nullable=False),
        sa.Column("expiresAt", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "createdAt", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column(
            "updatedAt", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # organization table (Better Auth organization plugin)
    op.create_table(
        "organization",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=True),
        sa.Column("logo", sa.Text(), nullable=True),
        sa.Column("metadata", sa.Text(), nullable=True),
        sa.Column(
            "createdAt", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    # member table (Better Auth organization plugin)
    op.create_table(
        "member",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("organizationId", sa.String(36), nullable=False),
        sa.Column("userId", sa.String(36), nullable=False),
        sa.Column("role", sa.String(50), nullable=False, server_default="member"),
        sa.Column(
            "createdAt", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.ForeignKeyConstraint(["organizationId"], ["organization.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["userId"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # invitation table (Better Auth organization plugin)
    op.create_table(
        "invitation",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("organizationId", sa.String(36), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("expiresAt", sa.DateTime(timezone=True), nullable=False),
        sa.Column("inviterId", sa.String(36), nullable=False),
        sa.Column(
            "createdAt", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.ForeignKeyConstraint(["organizationId"], ["organization.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["inviterId"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # jwks table (Better Auth JWT plugin)
    op.create_table(
        "jwks",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("publicKey", sa.Text(), nullable=False),
        sa.Column("privateKey", sa.Text(), nullable=False),
        sa.Column(
            "createdAt", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # ============================================
    # Create shop_settings table (our Shopify data)
    # ============================================
    op.create_table(
        "shop_settings",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("organization_id", sa.String(255), nullable=False),
        sa.Column("shopify_domain", sa.String(255), nullable=False),
        sa.Column("shopify_access_token", sa.Text(), nullable=True),
        sa.Column("shop_name", sa.String(255), nullable=True),
        sa.Column("shop_email", sa.String(255), nullable=True),
        sa.Column("plan", sa.String(50), nullable=False, server_default="free"),
        sa.Column("settings", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id"),
        sa.UniqueConstraint("shopify_domain"),
    )
    op.create_index("ix_shop_settings_organization_id", "shop_settings", ["organization_id"])
    op.create_index("ix_shop_settings_shopify_domain", "shop_settings", ["shopify_domain"])

    # ============================================
    # Update existing tables to use string organization_id
    # ============================================

    # Update products table
    op.alter_column(
        "products",
        "organization_id",
        existing_type=sa.UUID(),
        type_=sa.String(255),
        existing_nullable=False,
        postgresql_using="organization_id::text",
    )
    op.create_index("ix_products_organization_id", "products", ["organization_id"])
    op.create_index(
        "ix_products_organization_shopify_id",
        "products",
        ["organization_id", "shopify_product_id"],
        unique=True,
    )

    # Recreate vector index
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_products_embedding
        ON products USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
        """
    )

    # Update knowledge_articles table
    op.alter_column(
        "knowledge_articles",
        "organization_id",
        existing_type=sa.UUID(),
        type_=sa.String(255),
        existing_nullable=False,
        postgresql_using="organization_id::text",
    )

    # Update conversations table
    op.alter_column(
        "conversations",
        "organization_id",
        existing_type=sa.UUID(),
        type_=sa.String(255),
        existing_nullable=False,
        postgresql_using="organization_id::text",
    )


def downgrade() -> None:
    # This is a destructive migration - downgrade would require recreating
    # the old schema structure. For safety, we don't support automatic downgrade.
    raise NotImplementedError(
        "Downgrade not supported for Better Auth migration. Please restore from backup if needed."
    )

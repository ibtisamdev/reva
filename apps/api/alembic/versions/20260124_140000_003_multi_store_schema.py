"""Multi-store schema migration.

Revision ID: 003
Revises: 002
Create Date: 2026-01-24 14:00:00.000000

This migration:
1. Renames shop_settings to stores (platform-agnostic naming)
2. Creates store_integrations table for platform connections (Shopify, WooCommerce, etc.)
3. Changes products, knowledge_articles, conversations to reference store_id (UUID) instead of organization_id (string)
4. Supports multi-store per organization architecture
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ============================================
    # 1. Rename shop_settings to stores and restructure
    # ============================================

    # Drop old indexes on shop_settings
    op.drop_index("ix_shop_settings_organization_id", table_name="shop_settings")
    op.drop_index("ix_shop_settings_shopify_domain", table_name="shop_settings")

    # Rename table
    op.rename_table("shop_settings", "stores")

    # Drop shopify-specific columns (will be in store_integrations)
    op.drop_column("stores", "shopify_domain")
    op.drop_column("stores", "shopify_access_token")

    # Rename shop_* columns to store-agnostic names
    op.alter_column("stores", "shop_name", new_column_name="name")
    op.alter_column("stores", "shop_email", new_column_name="email")

    # Remove organization_id unique constraint (org can have multiple stores now)
    op.drop_constraint("uq_shop_settings_organization_id", "stores", type_="unique")

    # Add is_active column
    op.add_column(
        "stores",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
    )

    # Create new index for organization_id (not unique)
    op.create_index("ix_stores_organization_id", "stores", ["organization_id"])

    # ============================================
    # 2. Create store_integrations table
    # ============================================

    # Create platform_type enum
    op.execute(
        "CREATE TYPE platform_type AS ENUM ('shopify', 'woocommerce', 'bigcommerce', 'magento', 'custom')"
    )

    # Create integration_status enum
    op.execute(
        "CREATE TYPE integration_status AS ENUM ('pending', 'active', 'disconnected', 'error')"
    )

    op.create_table(
        "store_integrations",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("store_id", sa.UUID(), nullable=False),
        sa.Column(
            "platform",
            sa.Enum(
                "shopify", "woocommerce", "bigcommerce", "magento", "custom", name="platform_type"
            ),
            nullable=False,
        ),
        sa.Column("platform_store_id", sa.String(255), nullable=False),
        sa.Column("platform_domain", sa.String(255), nullable=False),
        sa.Column("credentials", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column(
            "status",
            sa.Enum("pending", "active", "disconnected", "error", name="integration_status"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("status_message", sa.Text(), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sync_error", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("store_id"),  # 1:1 relationship
    )
    op.create_index("ix_store_integrations_store_id", "store_integrations", ["store_id"])
    op.create_index(
        "ix_store_integrations_platform_domain", "store_integrations", ["platform_domain"]
    )

    # ============================================
    # 3. Update products table: organization_id (string) -> store_id (UUID)
    # ============================================

    # Drop old indexes
    op.drop_index("ix_products_organization_id", table_name="products")
    op.drop_index("ix_products_organization_shopify_id", table_name="products")

    # Drop old column and add new one
    op.drop_column("products", "organization_id")
    op.add_column(
        "products",
        sa.Column("store_id", sa.UUID(), nullable=False),
    )

    # Rename shopify_product_id to platform_product_id
    op.alter_column("products", "shopify_product_id", new_column_name="platform_product_id")
    op.alter_column(
        "products",
        "platform_product_id",
        existing_type=sa.BigInteger(),
        type_=sa.String(255),
        existing_nullable=False,
        postgresql_using="platform_product_id::text",
    )

    # Add foreign key and indexes
    op.create_foreign_key(
        "fk_products_store_id_stores",
        "products",
        "stores",
        ["store_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_products_store_id", "products", ["store_id"])
    op.create_index(
        "ix_products_store_platform_id",
        "products",
        ["store_id", "platform_product_id"],
        unique=True,
    )

    # ============================================
    # 4. Update knowledge_articles table: organization_id -> store_id
    # ============================================

    # Drop old index
    op.drop_index("ix_knowledge_articles_organization_id", table_name="knowledge_articles")

    # Drop old column and add new one
    op.drop_column("knowledge_articles", "organization_id")
    op.add_column(
        "knowledge_articles",
        sa.Column("store_id", sa.UUID(), nullable=False),
    )

    # Add foreign key and index
    op.create_foreign_key(
        "fk_knowledge_articles_store_id_stores",
        "knowledge_articles",
        "stores",
        ["store_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_knowledge_articles_store_id", "knowledge_articles", ["store_id"])

    # ============================================
    # 5. Update conversations table: organization_id -> store_id
    # ============================================

    # Drop old index
    op.drop_index("ix_conversations_organization_id", table_name="conversations")

    # Drop old column and add new one
    op.drop_column("conversations", "organization_id")
    op.add_column(
        "conversations",
        sa.Column("store_id", sa.UUID(), nullable=False),
    )

    # Add foreign key and index
    op.create_foreign_key(
        "fk_conversations_store_id_stores",
        "conversations",
        "stores",
        ["store_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_conversations_store_id", "conversations", ["store_id"])


def downgrade() -> None:
    # This is a significant schema change - downgrade not supported
    raise NotImplementedError(
        "Downgrade not supported for multi-store migration. Please restore from backup if needed."
    )

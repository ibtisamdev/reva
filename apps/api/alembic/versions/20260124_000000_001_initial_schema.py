"""Initial schema with all core tables.

Revision ID: 001
Revises:
Create Date: 2026-01-24 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Enable extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # Create enum types
    op.execute("CREATE TYPE user_role AS ENUM ('owner', 'admin', 'member')")
    op.execute("CREATE TYPE content_type AS ENUM ('faq', 'policy', 'guide', 'page')")
    op.execute("CREATE TYPE channel AS ENUM ('widget', 'email', 'whatsapp', 'sms')")
    op.execute("CREATE TYPE conversation_status AS ENUM ('active', 'resolved', 'escalated')")
    op.execute("CREATE TYPE message_role AS ENUM ('user', 'assistant', 'system')")

    # Create organizations table
    op.create_table(
        "organizations",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("shopify_domain", sa.String(255), nullable=False),
        sa.Column("shopify_access_token", sa.Text(), nullable=True),
        sa.Column("shop_name", sa.String(255), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organizations")),
        sa.UniqueConstraint("shopify_domain", name=op.f("uq_organizations_shopify_domain")),
    )
    op.create_index(
        op.f("ix_organizations_shopify_domain"),
        "organizations",
        ["shopify_domain"],
        unique=False,
    )

    # Create users table
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("clerk_user_id", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column(
            "role",
            postgresql.ENUM("owner", "admin", "member", name="user_role", create_type=False),
            nullable=False,
            server_default="member",
        ),
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
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_users_organization_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("clerk_user_id", name=op.f("uq_users_clerk_user_id")),
    )
    op.create_index(op.f("ix_users_organization_id"), "users", ["organization_id"], unique=False)
    op.create_index(op.f("ix_users_clerk_user_id"), "users", ["clerk_user_id"], unique=False)

    # Create products table
    op.create_table(
        "products",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("shopify_product_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("handle", sa.String(255), nullable=False),
        sa.Column("vendor", sa.String(255), nullable=True),
        sa.Column("product_type", sa.String(255), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("tags", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("variants", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("images", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_products_organization_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_products")),
    )
    op.create_index(
        "ix_products_organization_shopify_id",
        "products",
        ["organization_id", "shopify_product_id"],
        unique=True,
    )

    # Create knowledge_articles table
    op.create_table(
        "knowledge_articles",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "content_type",
            postgresql.ENUM(
                "faq", "policy", "guide", "page", name="content_type", create_type=False
            ),
            nullable=False,
            server_default="faq",
        ),
        sa.Column("source_url", sa.String(2048), nullable=True),
        sa.Column("extra_data", postgresql.JSONB(), nullable=False, server_default="{}"),
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
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_knowledge_articles_organization_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_knowledge_articles")),
    )
    op.create_index(
        op.f("ix_knowledge_articles_organization_id"),
        "knowledge_articles",
        ["organization_id"],
        unique=False,
    )

    # Create knowledge_chunks table
    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("article_id", sa.UUID(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column("extra_data", postgresql.JSONB(), nullable=False, server_default="{}"),
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
        sa.ForeignKeyConstraint(
            ["article_id"],
            ["knowledge_articles.id"],
            name=op.f("fk_knowledge_chunks_article_id_knowledge_articles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_knowledge_chunks")),
    )
    op.create_index(
        op.f("ix_knowledge_chunks_article_id"),
        "knowledge_chunks",
        ["article_id"],
        unique=False,
    )

    # Create conversations table
    op.create_table(
        "conversations",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("customer_email", sa.String(255), nullable=True),
        sa.Column("customer_name", sa.String(255), nullable=True),
        sa.Column("session_id", sa.String(64), nullable=False),
        sa.Column(
            "channel",
            postgresql.ENUM(
                "widget", "email", "whatsapp", "sms", name="channel", create_type=False
            ),
            nullable=False,
            server_default="widget",
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "active", "resolved", "escalated", name="conversation_status", create_type=False
            ),
            nullable=False,
            server_default="active",
        ),
        sa.Column("extra_data", postgresql.JSONB(), nullable=False, server_default="{}"),
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
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_conversations_organization_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_conversations")),
    )
    op.create_index(
        op.f("ix_conversations_organization_id"),
        "conversations",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_conversations_session_id"),
        "conversations",
        ["session_id"],
        unique=False,
    )

    # Create messages table
    op.create_table(
        "messages",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("conversation_id", sa.UUID(), nullable=False),
        sa.Column(
            "role",
            postgresql.ENUM("user", "assistant", "system", name="message_role", create_type=False),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tool_calls", postgresql.JSONB(), nullable=True),
        sa.Column("tool_results", postgresql.JSONB(), nullable=True),
        sa.Column("sources", postgresql.JSONB(), nullable=True),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            name=op.f("fk_messages_conversation_id_conversations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_messages")),
    )
    op.create_index(
        op.f("ix_messages_conversation_id"),
        "messages",
        ["conversation_id"],
        unique=False,
    )

    # Create vector indexes for similarity search (using IVFFlat)
    # These will be created after data is loaded in production
    # For now, we create basic btree indexes
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_products_embedding
        ON products USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_knowledge_chunks_embedding
        ON knowledge_chunks USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
        """
    )


def downgrade() -> None:
    # Drop vector indexes
    op.execute("DROP INDEX IF EXISTS ix_knowledge_chunks_embedding")
    op.execute("DROP INDEX IF EXISTS ix_products_embedding")

    # Drop tables in reverse order
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("knowledge_chunks")
    op.drop_table("knowledge_articles")
    op.drop_table("products")
    op.drop_table("users")
    op.drop_table("organizations")

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS message_role")
    op.execute("DROP TYPE IF EXISTS conversation_status")
    op.execute("DROP TYPE IF EXISTS channel")
    op.execute("DROP TYPE IF EXISTS content_type")
    op.execute("DROP TYPE IF EXISTS user_role")

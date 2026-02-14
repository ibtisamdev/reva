"""Pytest configuration and fixtures for the Reva API test suite.

Provides:
- Test database with table truncation cleanup per test
- Mock authentication (JWT bypass)
- Mock Redis (fakeredis)
- Disabled rate limiting
- Model factory fixtures for Store, Product, Conversation, Message,
  KnowledgeArticle, KnowledgeChunk, and StoreIntegration
"""

import uuid
from collections.abc import AsyncGenerator, Callable, Generator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import fakeredis.aioredis
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.auth import get_current_user, get_optional_user
from app.core.config import settings
from app.core.database import get_async_session
from app.core.deps import get_db, get_redis
from app.core.rate_limit import limiter
from app.main import app
from app.models.base import Base
from app.models.conversation import Channel, Conversation, ConversationStatus
from app.models.integration import IntegrationStatus, PlatformType, StoreIntegration
from app.models.knowledge import ContentType, KnowledgeArticle, KnowledgeChunk
from app.models.message import Message, MessageRole
from app.models.order_inquiry import InquiryResolution, InquiryType, OrderInquiry
from app.models.product import Product
from app.models.store import Store

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TEST_USER_ID = "test-user-id"
TEST_USER_EMAIL = "test@example.com"
TEST_ORG_ID = "test-org-id"
OTHER_ORG_ID = "other-org-id"

# ---------------------------------------------------------------------------
# Disable rate limiting globally for tests
# ---------------------------------------------------------------------------
limiter.enabled = False

# ---------------------------------------------------------------------------
# Session-scoped engine & table setup
# ---------------------------------------------------------------------------

_test_engine: Any = None
_test_session_factory: Any = None
_base_url = str(settings.database_url)
_TEST_DATABASE_URL = _base_url if _base_url.endswith("/reva_test") else _base_url.replace("/reva", "/reva_test")

# Tables to truncate after each test (reverse dependency order)
_TABLES_TO_TRUNCATE = [
    "order_inquiries",
    "messages",
    "conversations",
    "knowledge_chunks",
    "knowledge_articles",
    "products",
    "store_integrations",
    "stores",
]


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def _create_tables() -> AsyncGenerator[None, None]:
    """Create all tables once per test session in the reva_test database.

    Uses a separate reva_test database so tests never touch dev data.
    The engine is created here (not at module level) so that the connection
    pool is bound to the session-scoped event loop.

    Uses NullPool to avoid asyncpg connection-loop affinity issues with
    starlette's BaseHTTPMiddleware (which spawns sub-tasks).
    """
    global _test_engine, _test_session_factory  # noqa: PLW0603
    _test_engine = create_async_engine(
        _TEST_DATABASE_URL,
        echo=False,
        future=True,
        poolclass=NullPool,
    )
    _test_session_factory = async_sessionmaker(
        _test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with _test_engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Don't drop tables — they're shared with the dev database.
    # Per-test cleanup is handled by _cleanup_tables (TRUNCATE).
    await _test_engine.dispose()


# ---------------------------------------------------------------------------
# Per-test database session + cleanup
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(loop_scope="session")
async def db_session(_create_tables: None) -> AsyncGenerator[AsyncSession, None]:
    """Provide a database session for test setup (factory fixtures).

    Properly enters the async context manager so the connection is established.
    Uses loop_scope="session" to match the session-scoped engine/factory.
    Cleanup is handled by the ``_cleanup_tables`` autouse fixture.
    """
    async with _test_session_factory() as session:
        yield session


@pytest_asyncio.fixture(autouse=True)
async def _cleanup_tables() -> AsyncGenerator[None, None]:
    """Truncate all tables after each test to restore a clean state."""
    yield
    if _test_engine is not None:
        async with _test_engine.begin() as conn:
            await conn.execute(text(f"TRUNCATE {', '.join(_TABLES_TO_TRUNCATE)} CASCADE"))


# ---------------------------------------------------------------------------
# Fake Redis
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_redis() -> fakeredis.aioredis.FakeRedis:
    """Provide a fresh fakeredis instance per test."""
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


# ---------------------------------------------------------------------------
# Auth mock
# ---------------------------------------------------------------------------


@pytest.fixture
def auth_user() -> dict[str, Any]:
    """Return the default authenticated test user payload (mimics decoded JWT)."""
    return {
        "sub": TEST_USER_ID,
        "email": TEST_USER_EMAIL,
        "activeOrganizationId": TEST_ORG_ID,
    }


# ---------------------------------------------------------------------------
# Authenticated client (overrides DB, Redis, Auth)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def client(
    db_session: AsyncSession,  # noqa: ARG001  # Ensures _create_tables runs
    fake_redis: fakeredis.aioredis.FakeRedis,
    auth_user: dict[str, Any],
) -> AsyncGenerator[AsyncClient, None]:
    """Authenticated async test client with all dependencies overridden."""

    async def _override_session() -> AsyncGenerator[AsyncSession, None]:
        async with _test_session_factory() as s:
            yield s

    async def _override_user() -> dict[str, Any]:
        return auth_user

    async def _override_optional_user() -> dict[str, Any] | None:
        return auth_user

    async def _override_redis() -> AsyncGenerator[fakeredis.aioredis.FakeRedis, None]:
        yield fake_redis

    app.dependency_overrides[get_async_session] = _override_session
    app.dependency_overrides[get_db] = _override_session
    app.dependency_overrides[get_current_user] = _override_user
    app.dependency_overrides[get_optional_user] = _override_optional_user
    app.dependency_overrides[get_redis] = _override_redis

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Unauthenticated client (overrides DB & Redis only — no auth bypass)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def unauthed_client(
    db_session: AsyncSession,  # noqa: ARG001  # Ensures _create_tables runs
    fake_redis: fakeredis.aioredis.FakeRedis,
) -> AsyncGenerator[AsyncClient, None]:
    """Unauthenticated async test client. Auth is NOT overridden."""

    async def _override_session() -> AsyncGenerator[AsyncSession, None]:
        async with _test_session_factory() as s:
            yield s

    async def _override_redis() -> AsyncGenerator[fakeredis.aioredis.FakeRedis, None]:
        yield fake_redis

    app.dependency_overrides[get_async_session] = _override_session
    app.dependency_overrides[get_db] = _override_session
    app.dependency_overrides[get_redis] = _override_redis

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Lightweight client (no DB, no auth — for stateless endpoint tests)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def plain_client() -> AsyncGenerator[AsyncClient, None]:
    """Minimal async test client with NO dependency overrides."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


# ---------------------------------------------------------------------------
# Model Factories
# ---------------------------------------------------------------------------


@pytest.fixture
def store_factory(db_session: AsyncSession) -> Callable[..., Any]:
    """Factory that creates Store instances in the test database."""

    async def _create(
        *,
        name: str = "Test Store",
        organization_id: str = TEST_ORG_ID,
        email: str = "store@example.com",
        plan: str = "free",
        is_active: bool = True,
        settings_data: dict[str, Any] | None = None,
    ) -> Store:
        store = Store(
            organization_id=organization_id,
            name=name,
            email=email,
            plan=plan,
            is_active=is_active,
            settings=settings_data or {},
        )
        db_session.add(store)
        await db_session.commit()
        await db_session.refresh(store)
        return store

    return _create


@pytest.fixture
def product_factory(db_session: AsyncSession) -> Callable[..., Any]:
    """Factory that creates Product instances."""

    async def _create(
        *,
        store_id: UUID,
        title: str = "Test Product",
        platform_product_id: str | None = None,
        description: str | None = "A test product description",
        handle: str = "test-product",
        vendor: str | None = "Test Vendor",
        product_type: str | None = "Test Type",
        status: str = "active",
        tags: list[str] | None = None,
        variants: list[dict[str, Any]] | None = None,
        images: list[dict[str, Any]] | None = None,
        embedding: list[float] | None = None,
    ) -> Product:
        product = Product(
            store_id=store_id,
            platform_product_id=platform_product_id or str(uuid.uuid4()),
            title=title,
            description=description,
            handle=handle,
            vendor=vendor,
            product_type=product_type,
            status=status,
            tags=tags or [],
            variants=variants or [],
            images=images or [],
            embedding=embedding,
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)
        return product

    return _create


@pytest.fixture
def knowledge_article_factory(db_session: AsyncSession) -> Callable[..., Any]:
    """Factory that creates KnowledgeArticle instances with optional chunks."""

    async def _create(
        *,
        store_id: UUID,
        title: str = "Test Article",
        content: str = "This is test knowledge content.",
        content_type: ContentType = ContentType.FAQ,
        content_hash: str | None = None,
        source_url: str | None = None,
        num_chunks: int = 0,
        chunk_contents: list[str] | None = None,
    ) -> KnowledgeArticle:
        article = KnowledgeArticle(
            store_id=store_id,
            title=title,
            content=content,
            content_type=content_type,
            content_hash=content_hash,
            source_url=source_url,
        )
        db_session.add(article)
        await db_session.flush()

        # Create chunks if requested
        texts = chunk_contents or [f"Chunk {i} content." for i in range(num_chunks)]
        for idx, chunk_text in enumerate(texts):
            chunk = KnowledgeChunk(
                article_id=article.id,
                content=chunk_text,
                chunk_index=idx,
                token_count=len(chunk_text.split()),
            )
            db_session.add(chunk)

        await db_session.commit()
        await db_session.refresh(article)
        return article

    return _create


@pytest.fixture
def conversation_factory(db_session: AsyncSession) -> Callable[..., Any]:
    """Factory that creates Conversation instances."""

    async def _create(
        *,
        store_id: UUID,
        session_id: str | None = None,
        customer_email: str | None = None,
        customer_name: str | None = None,
        channel: Channel = Channel.WIDGET,
        status: ConversationStatus = ConversationStatus.ACTIVE,
    ) -> Conversation:
        conversation = Conversation(
            store_id=store_id,
            session_id=session_id or str(uuid.uuid4()),
            customer_email=customer_email,
            customer_name=customer_name,
            channel=channel,
            status=status,
        )
        db_session.add(conversation)
        await db_session.commit()
        await db_session.refresh(conversation)
        return conversation

    return _create


@pytest.fixture
def message_factory(db_session: AsyncSession) -> Callable[..., Any]:
    """Factory that creates Message instances."""

    async def _create(
        *,
        conversation_id: UUID,
        role: MessageRole = MessageRole.USER,
        content: str = "Test message",
        sources: list[dict[str, Any]] | None = None,
        tokens_used: int | None = None,
    ) -> Message:
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            sources=sources,
            tokens_used=tokens_used,
        )
        db_session.add(message)
        await db_session.commit()
        await db_session.refresh(message)
        return message

    return _create


@pytest.fixture
def integration_factory(db_session: AsyncSession) -> Callable[..., Any]:
    """Factory that creates StoreIntegration instances."""

    async def _create(
        *,
        store_id: UUID,
        platform: PlatformType = PlatformType.SHOPIFY,
        platform_store_id: str = "test-store.myshopify.com",
        platform_domain: str = "test-store.myshopify.com",
        credentials: dict[str, Any] | None = None,
        status: IntegrationStatus = IntegrationStatus.ACTIVE,
    ) -> StoreIntegration:
        integration = StoreIntegration(
            store_id=store_id,
            platform=platform,
            platform_store_id=platform_store_id,
            platform_domain=platform_domain,
            credentials=credentials or {},
            status=status,
        )
        db_session.add(integration)
        await db_session.commit()
        await db_session.refresh(integration)
        return integration

    return _create


@pytest.fixture
def order_inquiry_factory(db_session: AsyncSession) -> Callable[..., Any]:
    """Factory that creates OrderInquiry instances."""

    async def _create(
        *,
        store_id: UUID,
        conversation_id: UUID | None = None,
        customer_email: str | None = "customer@example.com",
        order_number: str | None = "#1001",
        inquiry_type: InquiryType = InquiryType.ORDER_STATUS,
        order_status: str | None = "paid",
        fulfillment_status: str | None = None,
        resolution: InquiryResolution | None = InquiryResolution.ANSWERED,
        extra_data: dict[str, Any] | None = None,
    ) -> OrderInquiry:
        inquiry = OrderInquiry(
            store_id=store_id,
            conversation_id=conversation_id,
            customer_email=customer_email,
            order_number=order_number,
            inquiry_type=inquiry_type,
            order_status=order_status,
            fulfillment_status=fulfillment_status,
            resolution=resolution,
            extra_data=extra_data or {},
        )
        db_session.add(inquiry)
        await db_session.commit()
        await db_session.refresh(inquiry)
        return inquiry

    return _create


# ---------------------------------------------------------------------------
# Convenience fixtures (pre-built models)
# ---------------------------------------------------------------------------


@pytest.fixture
async def store(store_factory: Callable[..., Any]) -> Store:
    """A default store belonging to the test user's organization."""
    return await store_factory()


@pytest.fixture
async def other_store(store_factory: Callable[..., Any]) -> Store:
    """A store belonging to a DIFFERENT organization (for multi-tenancy tests)."""
    return await store_factory(name="Other Store", organization_id=OTHER_ORG_ID)


# ---------------------------------------------------------------------------
# OpenAI Mocking Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_embedding() -> list[float]:
    """A mock 1536-dimensional embedding vector.

    Using a consistent vector allows us to control similarity matching
    in tests by giving chunks the same embedding as the query.
    """
    return [0.1] * 1536


@pytest.fixture
def mock_openai_response() -> dict[str, Any]:
    """Default mock response structure from OpenAI chat completion."""
    return {
        "id": "chatcmpl-test123",
        "object": "chat.completion",
        "created": 1234567890,
        "model": "gpt-4o",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "This is a mock AI response for testing.",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150,
        },
    }


@pytest.fixture
def mock_openai_chat(
    mock_openai_response: dict[str, Any],
) -> Generator[MagicMock, None, None]:
    """Patch ChatOpenAI in graph nodes to return mock LangChain AIMessage responses.

    The LangGraph workflow makes 2 LLM calls:
    1. classify_intent (returns non-JSON → falls back to small_talk/low confidence → clarify)
    2. The routed node (returns the mock response content)

    Usage:
        def test_something(mock_openai_chat):
            # LLM calls will return the mock response
            ...
    """
    from langchain_core.messages import AIMessage

    mock_ai_message = AIMessage(
        content=mock_openai_response["choices"][0]["message"]["content"],
        usage_metadata={
            "input_tokens": mock_openai_response["usage"]["prompt_tokens"],
            "output_tokens": mock_openai_response["usage"]["completion_tokens"],
            "total_tokens": mock_openai_response["usage"]["total_tokens"],
        },
    )

    with patch("app.services.graph.nodes.ChatOpenAI") as mock_class:
        mock_llm = MagicMock()
        mock_class.return_value = mock_llm

        # ainvoke returns the mock AIMessage (no tool calls)
        mock_llm.ainvoke = AsyncMock(return_value=mock_ai_message)
        # bind_tools returns the same mock (tools don't trigger in basic tests)
        mock_llm.bind_tools = MagicMock(return_value=mock_llm)

        yield mock_llm


@pytest.fixture
def mock_embedding_service(
    mock_embedding: list[float],
) -> Generator[MagicMock, None, None]:
    """Patch the embedding service singleton to return mock embeddings.

    This patches get_embedding_service() in retrieval_service.py and
    search_service.py so that vector similarity searches work with
    controlled embeddings.
    """
    with (
        patch("app.services.retrieval_service.get_embedding_service") as mock_get,
        patch("app.services.search_service.get_embedding_service") as mock_get_search,
        patch("app.services.recommendation_service.get_embedding_service") as mock_get_recommend,
    ):
        mock_service = MagicMock()
        mock_service.generate_embedding = AsyncMock(return_value=mock_embedding)
        mock_service.generate_embeddings_batch = AsyncMock(
            side_effect=lambda texts: [mock_embedding for _ in texts]
        )
        mock_get.return_value = mock_service
        mock_get_search.return_value = mock_service
        mock_get_recommend.return_value = mock_service
        yield mock_service


@pytest.fixture
def knowledge_chunk_factory(db_session: AsyncSession) -> Callable[..., Any]:
    """Factory that creates KnowledgeChunk instances with optional embedding.

    Unlike knowledge_article_factory which creates chunks inline, this allows
    creating chunks with specific embeddings for retrieval testing.
    """

    async def _create(
        *,
        article_id: UUID,
        content: str = "Test chunk content.",
        chunk_index: int = 0,
        token_count: int = 10,
        embedding: list[float] | None = None,
    ) -> KnowledgeChunk:
        chunk = KnowledgeChunk(
            article_id=article_id,
            content=content,
            chunk_index=chunk_index,
            token_count=token_count,
            embedding=embedding,
        )
        db_session.add(chunk)
        await db_session.commit()
        await db_session.refresh(chunk)
        return chunk

    return _create


# ---------------------------------------------------------------------------
# Shopify Testing Fixtures
# ---------------------------------------------------------------------------

# Test constants for Shopify
SHOPIFY_TEST_CLIENT_ID = "test-shopify-client-id"
SHOPIFY_TEST_CLIENT_SECRET = "test-shopify-client-secret"
SHOPIFY_TEST_SECRET_KEY = "test-secret-key-for-signing-install-tokens"
SHOPIFY_TEST_SHOP = "test-store.myshopify.com"


@pytest.fixture(autouse=True)
def set_shopify_test_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure Shopify settings are set for all tests.

    This is autouse=True so all tests have consistent Shopify config.
    """
    monkeypatch.setattr("app.core.config.settings.shopify_client_id", SHOPIFY_TEST_CLIENT_ID)
    monkeypatch.setattr(
        "app.core.config.settings.shopify_client_secret", SHOPIFY_TEST_CLIENT_SECRET
    )
    monkeypatch.setattr("app.core.config.settings.secret_key", SHOPIFY_TEST_SECRET_KEY)


@pytest.fixture
def shopify_webhook_signature() -> Callable[[bytes], str]:
    """Generate a valid Shopify webhook HMAC signature for a given body.

    Usage:
        signature = shopify_webhook_signature(b'{"id": 123}')
        headers = {"X-Shopify-Hmac-Sha256": signature, ...}
    """
    import base64
    import hashlib
    import hmac

    def _sign(body: bytes) -> str:
        return base64.b64encode(
            hmac.new(
                SHOPIFY_TEST_CLIENT_SECRET.encode(),
                body,
                hashlib.sha256,
            ).digest()
        ).decode()

    return _sign


@pytest.fixture
def shopify_webhook_headers(
    shopify_webhook_signature: Callable[[bytes], str],
) -> Callable[[bytes, str], dict[str, str]]:
    """Generate complete Shopify webhook headers for a given body and shop.

    Usage:
        body = b'{"id": 123, "title": "Product"}'
        headers = shopify_webhook_headers(body, "my-store.myshopify.com")
        response = await client.post("/webhooks/...", content=body, headers=headers)
    """

    def _headers(body: bytes, shop: str = SHOPIFY_TEST_SHOP) -> dict[str, str]:
        return {
            "X-Shopify-Hmac-Sha256": shopify_webhook_signature(body),
            "X-Shopify-Shop-Domain": shop,
            "Content-Type": "application/json",
        }

    return _headers


@pytest.fixture
def shopify_oauth_hmac() -> Callable[[dict[str, str]], str]:
    """Generate a valid Shopify OAuth callback HMAC for query params.

    Shopify's OAuth callback includes an HMAC computed over sorted query params
    (excluding the hmac param itself).

    Usage:
        params = {"code": "abc", "shop": "store.myshopify.com", "state": "nonce123"}
        hmac_value = shopify_oauth_hmac(params)
        params["hmac"] = hmac_value
    """
    import hashlib
    import hmac
    from urllib.parse import urlencode

    def _compute(params: dict[str, str]) -> str:
        # Sort params and exclude 'hmac' key
        filtered = {k: v for k, v in sorted(params.items()) if k != "hmac"}
        message = urlencode(filtered)
        return hmac.new(
            SHOPIFY_TEST_CLIENT_SECRET.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()

    return _compute


@pytest.fixture
def mock_shopify_token_exchange() -> Generator[MagicMock, None, None]:
    """Mock the Shopify OAuth token exchange HTTP call.

    Patches httpx.AsyncClient in oauth.py to return a mock access token + scopes.
    """
    with patch("app.integrations.shopify.oauth.httpx.AsyncClient") as mock_class:
        mock_client = AsyncMock()
        mock_class.return_value.__aenter__.return_value = mock_client

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "shpat_test_access_token_123",
            "scope": "read_products,read_content,read_orders",
        }
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        yield mock_client


@pytest.fixture
def mock_shopify_client() -> Generator[MagicMock, None, None]:
    """Mock the ShopifyClient class for route tests.

    This patches the ShopifyClient in shopify.py routes to avoid real API calls.
    """
    with patch("app.api.v1.shopify.ShopifyClient") as mock_class:
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance

        # Default async method returns
        mock_instance.register_webhooks = AsyncMock()
        mock_instance.delete_webhooks = AsyncMock()
        mock_instance.get_all_products = AsyncMock(return_value=[])

        yield mock_instance


@pytest.fixture
def mock_shopify_http() -> Generator[MagicMock, None, None]:
    """Mock httpx.AsyncClient for ShopifyClient unit tests.

    Provides fine-grained control over HTTP responses for testing the client.
    """
    with patch("app.integrations.shopify.client.httpx.AsyncClient") as mock_class:
        mock_client = AsyncMock()
        mock_class.return_value.__aenter__.return_value = mock_client

        # Default mock responses
        mock_get_response = MagicMock()
        mock_get_response.json.return_value = {"products": [], "webhooks": []}
        mock_get_response.headers = {}
        mock_get_response.raise_for_status = MagicMock()
        mock_get_response.is_success = True

        mock_post_response = MagicMock()
        mock_post_response.json.return_value = {"webhook": {"id": 1}}
        mock_post_response.is_success = True

        mock_client.get.return_value = mock_get_response
        mock_client.post.return_value = mock_post_response
        mock_client.delete.return_value = MagicMock()

        yield mock_client


@pytest.fixture
def mock_celery_shopify_tasks() -> Generator[dict[str, MagicMock], None, None]:
    """Mock all Shopify Celery tasks to prevent actual execution in route tests.

    Returns a dict of mocks for each task so tests can verify .delay() was called.
    """
    with (
        patch("app.api.v1.shopify.sync_products_full") as mock_sync_full,
        patch("app.api.v1.webhooks.shopify.sync_single_product") as mock_sync_single,
        patch("app.workers.tasks.shopify.generate_product_embeddings") as mock_gen_embed,
    ):
        yield {
            "sync_products_full": mock_sync_full,
            "sync_single_product": mock_sync_single,
            "generate_product_embeddings": mock_gen_embed,
        }


@pytest.fixture
def mock_embedding_service_for_tasks(
    mock_embedding: list[float],
) -> Generator[MagicMock, None, None]:
    """Mock embedding service specifically for Shopify task tests.

    Patches get_embedding_service in the tasks module.
    """
    with patch("app.workers.tasks.shopify.get_embedding_service") as mock_get:
        mock_service = MagicMock()
        mock_service.generate_embedding = AsyncMock(return_value=mock_embedding)
        mock_service.generate_embeddings_batch = AsyncMock(
            side_effect=lambda texts: [mock_embedding for _ in texts]
        )
        mock_get.return_value = mock_service
        yield mock_service


@pytest.fixture
def sample_shopify_product() -> dict[str, Any]:
    """A sample Shopify product JSON as returned by the Admin API."""
    return {
        "id": 1234567890,
        "title": "Test Product",
        "body_html": "<p>A great product</p>",
        "handle": "test-product",
        "vendor": "Test Vendor",
        "product_type": "Widget",
        "status": "active",
        "tags": "sale, featured",
        "variants": [
            {
                "id": 111,
                "title": "Default Title",
                "price": "29.99",
                "sku": "TEST-001",
                "inventory_quantity": 100,
            }
        ],
        "images": [
            {
                "id": 222,
                "src": "https://cdn.shopify.com/test.jpg",
                "alt": "Test image",
                "position": 1,
            }
        ],
    }


@pytest.fixture
def sample_shopify_products() -> list[dict[str, Any]]:
    """Multiple sample Shopify products for pagination/batch tests."""
    return [
        {
            "id": 1001,
            "title": "Product One",
            "body_html": "<p>Description one</p>",
            "handle": "product-one",
            "vendor": "Vendor A",
            "product_type": "Type A",
            "status": "active",
            "tags": "new",
            "variants": [{"id": 1, "title": "Default", "price": "10.00"}],
            "images": [],
        },
        {
            "id": 1002,
            "title": "Product Two",
            "body_html": "<p>Description two</p>",
            "handle": "product-two",
            "vendor": "Vendor B",
            "product_type": "Type B",
            "status": "active",
            "tags": "sale, clearance",
            "variants": [
                {"id": 2, "title": "Small", "price": "20.00"},
                {"id": 3, "title": "Large", "price": "25.00"},
            ],
            "images": [{"id": 10, "src": "https://example.com/img.jpg"}],
        },
        {
            "id": 1003,
            "title": "Product Three",
            "body_html": None,
            "handle": "product-three",
            "vendor": None,
            "product_type": None,
            "status": "draft",
            "tags": "",
            "variants": [],
            "images": [],
        },
    ]


# ---------------------------------------------------------------------------
# PDF Testing Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_pdf_bytes() -> bytes:
    """Generate a minimal valid PDF with text content for testing.

    Creates a 2-page PDF with known text content that can be verified
    after extraction.
    """
    import io

    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)

    # Page 1
    c.drawString(100, 750, "Page 1: This is test content for the first page.")
    c.drawString(100, 730, "It contains important information about shipping.")
    c.showPage()

    # Page 2
    c.drawString(100, 750, "Page 2: This is the second page of the document.")
    c.drawString(100, 730, "Returns policy: 30 days for full refund.")
    c.showPage()

    c.save()
    return buffer.getvalue()


@pytest.fixture
def empty_pdf_bytes() -> bytes:
    """Generate a PDF with no extractable text (blank pages).

    Used to test handling of PDFs that have pages but no text content.
    """
    import io

    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    # Create a blank page with no text
    c.showPage()
    c.save()
    return buffer.getvalue()


@pytest.fixture
def corrupted_pdf_bytes() -> bytes:
    """Return truncated/corrupted PDF bytes for error handling tests."""
    # Start of a PDF but truncated - will fail to parse
    return b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n"


# ---------------------------------------------------------------------------
# Knowledge Service Mocking Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_knowledge_embedding_service(
    mock_embedding: list[float],
) -> Generator[MagicMock, None, None]:
    """Mock embedding service for knowledge_service.py tests.

    Uses real chunk_text and count_tokens (no external API calls),
    but mocks embedding generation.
    """
    with patch("app.services.knowledge_service.get_embedding_service") as mock_get:
        mock_service = MagicMock()

        # Import real service for non-API methods
        from app.services.embedding_service import EmbeddingService

        real_service = EmbeddingService()

        # Use real implementations for local-only methods
        mock_service.chunk_text = real_service.chunk_text
        mock_service.count_tokens = real_service.count_tokens

        # Mock embedding generation
        mock_service.generate_embeddings_batch = AsyncMock(
            side_effect=lambda texts: [mock_embedding for _ in texts]
        )
        mock_service.generate_embedding = AsyncMock(return_value=mock_embedding)

        mock_get.return_value = mock_service
        yield mock_service


@pytest.fixture
def mock_knowledge_embedding_service_failure() -> Generator[MagicMock, None, None]:
    """Mock embedding service that raises an exception on embedding generation.

    Used to test error handling when OpenAI API fails.
    """
    with patch("app.services.knowledge_service.get_embedding_service") as mock_get:
        mock_service = MagicMock()

        # Import real service for non-API methods
        from app.services.embedding_service import EmbeddingService

        real_service = EmbeddingService()

        # Use real implementations for local-only methods
        mock_service.chunk_text = real_service.chunk_text
        mock_service.count_tokens = real_service.count_tokens

        # Mock embedding generation to fail
        mock_service.generate_embeddings_batch = AsyncMock(
            side_effect=Exception("OpenAI API error: rate limit exceeded")
        )

        mock_get.return_value = mock_service
        yield mock_service


@pytest.fixture
def mock_celery_embedding_task() -> Generator[MagicMock, None, None]:
    """Mock the Celery embedding task to prevent actual execution.

    Patches in the workers.tasks.embedding module where it's defined.
    """
    with patch("app.workers.tasks.embedding.process_article_embeddings") as mock_task:
        # Mock the .delay() method
        mock_task.delay = MagicMock()
        yield mock_task


@pytest.fixture
def mock_async_session_maker(_create_tables: None) -> Generator[None, None, None]:
    """Patch async_session_maker so background tasks use the test database.

    Tasks like _process_article_embeddings_async create their own sessions
    via async_session_maker, which defaults to the dev database. This
    redirects them to reva_test.
    """
    with patch("app.workers.tasks.embedding.async_session_maker", _test_session_factory):
        yield


@pytest.fixture
def mock_url_fetch() -> Generator[MagicMock, None, None]:
    """Mock fetch_url_content for knowledge route tests.

    Patches in the url_service module where it's defined, since
    the knowledge route imports it inside the function.
    """
    with patch("app.services.url_service.fetch_url_content") as mock_fetch:

        async def mock_fetch_async(_url: str) -> tuple[str, str]:
            return ("This is extracted content from the URL.", "Page Title")

        mock_fetch.side_effect = mock_fetch_async
        yield mock_fetch


@pytest.fixture
def mock_pdf_extract() -> Generator[MagicMock, None, None]:
    """Mock extract_text_from_pdf for knowledge route tests.

    Patches in the pdf_service module where it's defined.
    """
    with patch("app.services.pdf_service.extract_text_from_pdf") as mock_extract:
        mock_extract.return_value = "This is extracted text from the PDF document."
        yield mock_extract


# ---------------------------------------------------------------------------
# Order Service Testing Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_shopify_order() -> dict[str, Any]:
    """A sample Shopify order JSON as returned by the Admin API.

    Includes line items, customer info, shipping address, and financial/fulfillment status.
    """
    return {
        "id": 5551234567890,
        "name": "#1001",
        "email": "customer@example.com",
        "financial_status": "paid",
        "fulfillment_status": None,
        "created_at": "2024-06-15T10:30:00-04:00",
        "total_price": "79.98",
        "currency": "USD",
        "cancelled_at": None,
        "customer": {
            "first_name": "Jane",
            "last_name": "Doe",
        },
        "shipping_address": {
            "city": "New York",
            "province": "NY",
        },
        "line_items": [
            {
                "title": "Widget Pro",
                "quantity": 2,
                "price": "39.99",
                "variant_title": "Blue / Large",
            },
        ],
    }


@pytest.fixture
def sample_fulfillments() -> list[dict[str, Any]]:
    """Sample fulfillment data as returned by Shopify's order fulfillments endpoint."""
    return [
        {
            "status": "success",
            "tracking_number": "1Z999AA10123456784",
            "tracking_url": "https://wwwapps.ups.com/tracking/tracking.cgi?tracknum=1Z999AA10123456784",
            "tracking_company": "UPS",
            "shipment_status": "delivered",
            "created_at": "2024-06-16T14:00:00-04:00",
        },
    ]


@pytest.fixture
def mock_decrypt_token() -> Generator[MagicMock, None, None]:
    """Patch decrypt_token in the order_service module to return a fixed token.

    Prevents tests from needing real encryption keys.
    """
    with patch("app.services.order_service.decrypt_token") as mock_fn:
        mock_fn.return_value = "shpat_decrypted_test_token"
        yield mock_fn

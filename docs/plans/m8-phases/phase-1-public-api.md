# Phase 1: Public REST API

> **Parent:** [M8 Developer Platform](../m8-developer-platform.md)  
> **Duration:** 1.5 weeks  
> **Status:** Not Started  
> **Dependencies:** M1-M7 complete

---

## Goal

Build a comprehensive public REST API with OAuth 2.0 authentication, rate limiting, and versioning to enable programmatic access to all Reva data and actions.

---

## Tasks

### 1.1 OAuth 2.0 Authentication System

**Location:** `apps/api/app/services/oauth.py`

- [ ] Implement OAuth 2.0 authorization code flow
- [ ] Create OAuth application registration endpoint
- [ ] Generate and validate access tokens (JWT)
- [ ] Implement token refresh mechanism
- [ ] Support granular scopes for permissions:
  - [ ] `conversations:read` - Read conversation data
  - [ ] `conversations:write` - Send messages programmatically
  - [ ] `customers:read` - Access customer information
  - [ ] `customers:write` - Update customer data
  - [ ] `knowledge:read` - Read knowledge base
  - [ ] `knowledge:write` - Manage knowledge content
  - [ ] `analytics:read` - Access usage metrics
  - [ ] `webhooks:write` - Manage webhook subscriptions

**OAuth Flow Example:**

```python
# Authorization URL
GET /oauth/authorize?client_id=abc&redirect_uri=https://app.com/callback&scope=conversations:read

# Token exchange
POST /oauth/token
{
  "grant_type": "authorization_code",
  "code": "auth_code_123",
  "client_id": "abc",
  "client_secret": "secret"
}

# Response
{
  "access_token": "eyJ...",
  "refresh_token": "refresh_123",
  "expires_in": 3600,
  "scope": "conversations:read"
}
```

### 1.2 API Key Management

**Location:** `apps/api/app/models/api_keys.py`

- [ ] Create `api_keys` table with schema:
  ```sql
  CREATE TABLE api_keys (
    id UUID PRIMARY KEY,
    organization_id UUID REFERENCES organizations(id),
    name VARCHAR(255) NOT NULL,
    key_hash VARCHAR(255) NOT NULL,
    scopes_json JSONB NOT NULL,
    rate_limit INTEGER DEFAULT 60,
    last_used_at TIMESTAMP,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
  );
  ```
- [ ] Implement API key generation (secure random + prefix)
- [ ] Hash storage (never store plain keys)
- [ ] Scope validation middleware
- [ ] Usage tracking and analytics

**API Key Format:**

```
reva_live_sk_1234567890abcdef  # Production
reva_test_sk_abcdef1234567890  # Sandbox
```

### 1.3 Rate Limiting Infrastructure

**Location:** `apps/api/app/core/rate_limit.py`

- [ ] Implement token bucket algorithm with Redis
- [ ] Support different limits per API key tier:
  ```python
  RATE_LIMITS = {
      "free": {"requests_per_minute": 60, "burst": 10},
      "pro": {"requests_per_minute": 300, "burst": 50},
      "enterprise": {"requests_per_minute": 1000, "burst": 100}
  }
  ```
- [ ] Rate limit headers in responses:
  ```
  X-RateLimit-Limit: 60
  X-RateLimit-Remaining: 45
  X-RateLimit-Reset: 1643723400
  ```
- [ ] Graceful degradation (429 Too Many Requests)
- [ ] Rate limit bypass for internal services

### 1.4 Public API Endpoints

**Location:** `apps/api/app/api/v1/public/`

Create comprehensive REST endpoints for all resources:

#### Conversations API

```python
# apps/api/app/api/v1/public/conversations.py

@router.get("/conversations")
async def list_conversations(
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None,
    since: Optional[datetime] = None,
    auth: OAuth2Token = Depends(require_scope("conversations:read"))
):
    """List conversations with pagination and filtering."""

@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: UUID,
    auth: OAuth2Token = Depends(require_scope("conversations:read"))
):
    """Get conversation details with message history."""

@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: UUID,
    message: MessageCreate,
    auth: OAuth2Token = Depends(require_scope("conversations:write"))
):
    """Send message programmatically."""
```

#### Customers API

```python
# apps/api/app/api/v1/public/customers.py

@router.get("/customers")
async def list_customers(
    limit: int = 50,
    offset: int = 0,
    email: Optional[str] = None,
    auth: OAuth2Token = Depends(require_scope("customers:read"))
):
    """List customers with search and pagination."""

@router.patch("/customers/{customer_id}")
async def update_customer(
    customer_id: UUID,
    updates: CustomerUpdate,
    auth: OAuth2Token = Depends(require_scope("customers:write"))
):
    """Update customer information."""
```

#### Knowledge API

```python
# apps/api/app/api/v1/public/knowledge.py

@router.post("/knowledge")
async def create_knowledge(
    knowledge: KnowledgeCreate,
    auth: OAuth2Token = Depends(require_scope("knowledge:write"))
):
    """Create knowledge base entry."""

@router.delete("/knowledge/{knowledge_id}")
async def delete_knowledge(
    knowledge_id: UUID,
    auth: OAuth2Token = Depends(require_scope("knowledge:write"))
):
    """Delete knowledge entry."""
```

#### Analytics API

```python
# apps/api/app/api/v1/public/analytics.py

@router.get("/analytics")
async def get_analytics(
    metrics: List[str] = Query(...),
    period: str = "daily",
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    auth: OAuth2Token = Depends(require_scope("analytics:read"))
):
    """Get usage analytics and metrics."""
```

### 1.5 API Versioning

**Location:** `apps/api/app/api/v1/public/__init__.py`

- [ ] Implement versioning strategy:
  - URL versioning: `/api/v1/`, `/api/v2/`
  - Header versioning: `API-Version: 2024-01-01`
- [ ] Backward compatibility guarantees
- [ ] Deprecation warnings and timeline
- [ ] Version-specific documentation

### 1.6 Error Handling & Validation

**Location:** `apps/api/app/schemas/public/`

- [ ] Standardized error response format:
  ```json
  {
    "error": {
      "code": "INVALID_REQUEST",
      "message": "The request is invalid",
      "details": {
        "field": "email",
        "issue": "Invalid email format"
      },
      "request_id": "req_123456"
    }
  }
  ```
- [ ] Comprehensive input validation with Pydantic
- [ ] Request/response logging for debugging
- [ ] Request ID tracking for support

---

## Files to Create/Modify

| File                                   | Action | Purpose                     |
| -------------------------------------- | ------ | --------------------------- |
| `app/services/oauth.py`                | Create | OAuth 2.0 implementation    |
| `app/models/api_keys.py`               | Create | API key data model          |
| `app/models/oauth_applications.py`     | Create | OAuth app registration      |
| `app/core/rate_limit.py`               | Create | Rate limiting middleware    |
| `app/core/auth.py`                     | Modify | Add OAuth token validation  |
| `app/api/v1/public/__init__.py`        | Create | Public API router           |
| `app/api/v1/public/conversations.py`   | Create | Conversations endpoints     |
| `app/api/v1/public/customers.py`       | Create | Customers endpoints         |
| `app/api/v1/public/knowledge.py`       | Create | Knowledge endpoints         |
| `app/api/v1/public/analytics.py`       | Create | Analytics endpoints         |
| `app/api/v1/public/products.py`        | Create | Products endpoints          |
| `app/schemas/public/auth.py`           | Create | OAuth schemas               |
| `app/schemas/public/conversations.py`  | Create | Public conversation schemas |
| `app/schemas/public/customers.py`      | Create | Public customer schemas     |
| `app/schemas/public/errors.py`         | Create | Standardized error schemas  |
| `alembic/versions/xxx_add_api_keys.py` | Create | Database migration          |

---

## Dependencies

```toml
# Add to pyproject.toml
python-jose = "^3.3"        # JWT token handling
passlib = "^1.7"            # Password hashing
redis = "^5.0"              # Rate limiting storage
pydantic-settings = "^2.0"  # Configuration management
```

---

## Testing

- [ ] Unit tests for OAuth flow (authorization, token exchange, refresh)
- [ ] Unit tests for rate limiting (within limits, exceeded limits)
- [ ] Integration tests for all API endpoints
- [ ] Load testing for rate limiting under high traffic
- [ ] Security testing for token validation and scope enforcement
- [ ] API contract testing with generated OpenAPI specs

**Example Test:**

```python
@pytest.mark.asyncio
async def test_oauth_authorization_flow():
    # Test authorization URL generation
    auth_url = oauth_service.get_authorization_url(
        client_id="test_client",
        redirect_uri="https://app.com/callback",
        scope="conversations:read"
    )
    assert "client_id=test_client" in auth_url

    # Test token exchange
    token = await oauth_service.exchange_code(
        code="auth_code_123",
        client_id="test_client",
        client_secret="secret"
    )
    assert token.access_token
    assert "conversations:read" in token.scope

@pytest.mark.asyncio
async def test_rate_limiting():
    # Make requests up to limit
    for i in range(60):
        response = await client.get("/api/v1/conversations", headers=auth_headers)
        assert response.status_code == 200

    # Next request should be rate limited
    response = await client.get("/api/v1/conversations", headers=auth_headers)
    assert response.status_code == 429
    assert "X-RateLimit-Reset" in response.headers
```

---

## Acceptance Criteria

1. **OAuth Flow Works:** Can register app, get authorization, exchange for tokens
2. **API Authentication:** All endpoints require valid tokens with correct scopes
3. **Rate Limiting:** Requests are limited per API key tier, with proper headers
4. **CRUD Operations:** Can create, read, update, delete all resources via API
5. **Error Handling:** Consistent error format with helpful messages
6. **Multi-tenant:** Each organization only sees their own data
7. **Performance:** API responses under 200ms for simple queries
8. **Documentation:** OpenAPI spec generates automatically from code

---

## Notes

- Start with read-only endpoints, add write operations iteratively
- Use existing internal services where possible (don't duplicate logic)
- Consider GraphQL for future versions if REST becomes limiting
- Implement comprehensive logging for API usage analytics

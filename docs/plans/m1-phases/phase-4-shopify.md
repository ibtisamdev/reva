# Phase 4: Shopify Integration

> **Parent:** [M1 Product Q&A Bot](../m1-product-qa.md)  
> **Duration:** 1 week  
> **Status:** Not Started  
> **Depends on:** Phase 1 (RAG Pipeline), Phase 3 (Dashboard)

---

## Goal

Connect to Shopify stores via OAuth, sync products automatically, and include product data in the AI's knowledge base.

---

## Prerequisites

Before starting this phase:

1. **Shopify Partner Account** - Create at [partners.shopify.com](https://partners.shopify.com)
2. **Development Store** - Create a dev store for testing
3. **App Credentials** - Create an app to get API key and secret

---

## Tasks

### 4.1 Shopify Partner Setup

**Not code - manual setup:**

- [ ] Create Shopify Partner account (if not exists)
- [ ] Create development store for testing
- [ ] Create a new app in Partner Dashboard
- [ ] Configure app URLs:
  - App URL: `https://app.reva.ai/dashboard`
  - Allowed redirection URLs: `https://api.reva.ai/api/v1/shopify/callback`
- [ ] Note API key and secret
- [ ] Add to environment variables

**Environment variables:**

```bash
SHOPIFY_CLIENT_ID=your_api_key
SHOPIFY_CLIENT_SECRET=your_api_secret
SHOPIFY_SCOPES=read_products,read_content
```

### 4.2 Shopify OAuth Flow

**Location:** `apps/api/app/api/v1/shopify.py`

- [ ] `GET /api/v1/shopify/install?shop={shop}` - Start OAuth
- [ ] `GET /api/v1/shopify/callback` - Handle OAuth callback
- [ ] Validate HMAC signature on callback
- [ ] Exchange code for access token
- [ ] Store access token encrypted in database
- [ ] Create/update Integration record

**OAuth flow:**

```
1. Merchant clicks "Connect Shopify" in dashboard
2. Redirect to: /api/v1/shopify/install?shop=mystore.myshopify.com
3. API redirects to Shopify OAuth URL
4. Merchant approves permissions
5. Shopify redirects to /api/v1/shopify/callback?code=xxx&shop=xxx
6. API exchanges code for access token
7. API stores token, redirects to dashboard
```

**Implementation:**

```python
# apps/api/app/api/v1/shopify.py

@router.get("/install")
async def install(shop: str, session: AsyncSession = Depends(get_session)):
    """Start Shopify OAuth flow."""
    if not shop.endswith(".myshopify.com"):
        raise HTTPException(400, "Invalid shop domain")

    nonce = secrets.token_urlsafe(16)
    # Store nonce in Redis with TTL

    redirect_uri = f"{settings.API_URL}/api/v1/shopify/callback"
    auth_url = (
        f"https://{shop}/admin/oauth/authorize"
        f"?client_id={settings.SHOPIFY_CLIENT_ID}"
        f"&scope={settings.SHOPIFY_SCOPES}"
        f"&redirect_uri={redirect_uri}"
        f"&state={nonce}"
    )
    return RedirectResponse(auth_url)

@router.get("/callback")
async def callback(
    code: str,
    shop: str,
    state: str,
    hmac: str,
    session: AsyncSession = Depends(get_session)
):
    """Handle Shopify OAuth callback."""
    # 1. Verify HMAC
    # 2. Verify state/nonce
    # 3. Exchange code for token
    # 4. Store token
    # 5. Trigger initial sync
    # 6. Redirect to dashboard
    ...
```

### 4.3 Product Sync - Initial

**Location:** `apps/api/app/workers/shopify_tasks.py`

- [ ] Create Celery task for full product sync
- [ ] Fetch all products from Shopify API (paginated)
- [ ] Store products in database
- [ ] Generate embeddings for product descriptions
- [ ] Add products to knowledge base

**Shopify API endpoint:**

```
GET /admin/api/2024-01/products.json?limit=250
```

**Product data to store:**

- id, title, handle, description (HTML)
- variants (with prices, inventory)
- images
- tags, product_type, vendor

**Celery task:**

```python
@celery_app.task
def sync_products_full(store_id: str):
    """Full product sync from Shopify."""
    store = get_store(store_id)
    integration = get_integration(store_id, "shopify")

    shopify = ShopifyClient(integration.access_token)

    products = []
    for page in shopify.get_products_paginated():
        products.extend(page)

    # Upsert products
    for product in products:
        upsert_product(store_id, product)

    # Generate embeddings
    generate_product_embeddings.delay(store_id)
```

### 4.4 Product Sync - Incremental (Webhooks)

**Location:** `apps/api/app/api/v1/webhooks/shopify.py`

- [ ] Register webhooks on app install
- [ ] `POST /api/v1/webhooks/shopify/products/create`
- [ ] `POST /api/v1/webhooks/shopify/products/update`
- [ ] `POST /api/v1/webhooks/shopify/products/delete`
- [ ] Verify webhook HMAC signature
- [ ] Update product in database
- [ ] Regenerate embeddings if description changed

**Webhooks to register:**

```python
SHOPIFY_WEBHOOKS = [
    {"topic": "products/create", "address": f"{API_URL}/webhooks/shopify/products/create"},
    {"topic": "products/update", "address": f"{API_URL}/webhooks/shopify/products/update"},
    {"topic": "products/delete", "address": f"{API_URL}/webhooks/shopify/products/delete"},
]
```

### 4.5 Product Embeddings

**Location:** `apps/api/app/knowledge/products.py`

- [ ] Convert product data to embedable text
- [ ] Include: title, description, tags, variants, price
- [ ] Generate embeddings using OpenAI
- [ ] Store in knowledge table with `source_type = 'product'`

**Product to text conversion:**

```python
def product_to_text(product: Product) -> str:
    """Convert product to searchable text."""
    parts = [
        f"Product: {product.title}",
        f"Description: {strip_html(product.description)}",
        f"Price: ${product.price}",
        f"Tags: {', '.join(product.tags)}",
    ]

    if product.variants:
        sizes = [v.title for v in product.variants if v.title != "Default"]
        if sizes:
            parts.append(f"Available sizes: {', '.join(sizes)}")

    return "\n".join(parts)
```

### 4.6 Store Pages Sync

**Location:** `apps/api/app/workers/shopify_tasks.py`

- [ ] Fetch Shopify pages (policies, about, FAQ)
- [ ] Extract text content from HTML
- [ ] Add to knowledge base

**Shopify API endpoint:**

```
GET /admin/api/2024-01/pages.json
```

**Pages to sync:**

- Shipping policy
- Refund policy
- Privacy policy
- Terms of service
- Custom pages (FAQ, About, etc.)

### 4.7 Dashboard - Shopify Connection

**Location:** `apps/web/src/app/dashboard/settings/integrations/`

- [ ] Create integrations settings page
- [ ] "Connect Shopify" button
- [ ] Show connection status
- [ ] Display synced product count
- [ ] "Resync Products" button
- [ ] Disconnect option

**UI Layout:**

```
┌─────────────────────────────────────────────────────────┐
│ Integrations                                            │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ Shopify                                                 │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ ✓ Connected to mystore.myshopify.com                │ │
│ │                                                     │ │
│ │ Products synced: 156                                │ │
│ │ Last sync: 2 hours ago                              │ │
│ │                                                     │ │
│ │ [Resync Products]              [Disconnect]         │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 4.8 Dashboard - Products List

**Location:** `apps/web/src/app/dashboard/products/`

- [ ] Create products list page `/dashboard/products`
- [ ] Show synced products from Shopify
- [ ] Display: image, title, price, sync status
- [ ] Link to Shopify admin for editing

---

## Files to Create/Modify

### Backend

| File                                   | Action | Purpose              |
| -------------------------------------- | ------ | -------------------- |
| `app/api/v1/shopify.py`                | Create | OAuth endpoints      |
| `app/api/v1/webhooks/shopify.py`       | Create | Webhook handlers     |
| `app/integrations/shopify/__init__.py` | Create | Package init         |
| `app/integrations/shopify/client.py`   | Create | Shopify API client   |
| `app/integrations/shopify/oauth.py`    | Create | OAuth helpers        |
| `app/integrations/shopify/webhooks.py` | Create | Webhook verification |
| `app/workers/shopify_tasks.py`         | Create | Celery tasks         |
| `app/knowledge/products.py`            | Create | Product embeddings   |
| `app/schemas/shopify.py`               | Create | Pydantic models      |

### Frontend

| File                                           | Action | Purpose           |
| ---------------------------------------------- | ------ | ----------------- |
| `app/dashboard/settings/integrations/page.tsx` | Create | Integrations page |
| `app/dashboard/products/page.tsx`              | Create | Products list     |
| `components/integrations/ShopifyConnect.tsx`   | Create | Connect button    |
| `components/products/ProductList.tsx`          | Create | Product list      |

---

## API Endpoints

| Endpoint                     | Method | Purpose              |
| ---------------------------- | ------ | -------------------- |
| `/api/v1/shopify/install`    | GET    | Start OAuth          |
| `/api/v1/shopify/callback`   | GET    | OAuth callback       |
| `/api/v1/shopify/disconnect` | POST   | Disconnect store     |
| `/api/v1/shopify/sync`       | POST   | Trigger manual sync  |
| `/api/v1/webhooks/shopify/*` | POST   | Webhook handlers     |
| `/api/v1/products`           | GET    | List synced products |

---

## Dependencies

```toml
# Add to pyproject.toml
shopify-api = "^12.0"   # Or use httpx directly
cryptography = "^41.0"  # For token encryption
```

---

## Security Considerations

1. **Token Storage:** Encrypt access tokens at rest
2. **HMAC Verification:** Verify all webhook signatures
3. **Nonce Validation:** Prevent CSRF in OAuth flow
4. **Scope Limitation:** Only request needed scopes

**Encryption helper:**

```python
from cryptography.fernet import Fernet

def encrypt_token(token: str) -> str:
    f = Fernet(settings.ENCRYPTION_KEY)
    return f.encrypt(token.encode()).decode()

def decrypt_token(encrypted: str) -> str:
    f = Fernet(settings.ENCRYPTION_KEY)
    return f.decrypt(encrypted.encode()).decode()
```

---

## Testing

- [ ] Test: OAuth flow with development store
- [ ] Test: Product sync fetches all products
- [ ] Test: Webhook creates/updates products
- [ ] Test: Webhook HMAC verification
- [ ] Test: Product embeddings are generated
- [ ] Test: Products appear in AI responses

---

## Acceptance Criteria

1. Merchant can connect their Shopify store via OAuth
2. Products sync automatically after connection
3. Product updates sync via webhooks
4. Products are included in AI knowledge base
5. AI can answer questions about specific products
6. Dashboard shows synced products

---

## Shopify API Reference

- [OAuth Documentation](https://shopify.dev/docs/apps/auth/oauth)
- [Products API](https://shopify.dev/docs/api/admin-rest/2024-01/resources/product)
- [Webhooks](https://shopify.dev/docs/apps/webhooks)
- [HMAC Verification](https://shopify.dev/docs/apps/auth/oauth/getting-started#verify-a-request)

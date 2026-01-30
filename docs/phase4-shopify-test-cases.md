# Phase 4: Shopify Integration - Test Cases

Reference for writing automated tests. Each section maps to an API endpoint or UI flow tested during manual browser testing.

---

## Backend API Tests

### 1. `GET /api/v1/shopify/install`

| Case | Input | Expected |
|------|-------|----------|
| Valid shop domain | `shop=mystore.myshopify.com&store_id=<uuid>` | 307 redirect to `https://mystore.myshopify.com/admin/oauth/authorize?...` with correct `client_id`, `scope`, `redirect_uri`, `state` |
| Invalid shop domain | `shop=invalid-domain.com&store_id=<uuid>` | 400 `"Invalid shop domain"` |
| Missing shop param | `store_id=<uuid>` | 422 validation error |
| Missing store_id | `shop=x.myshopify.com` | 422 validation error |
| Nonce stored in Redis | valid request | Redis key `shopify_oauth:{nonce}` exists with value `{store_id}:{shop}`, TTL = 600s |

**Notes:**
- This endpoint has no auth (called via browser redirect).
- Security relies on the nonce/state parameter validated in `/callback`.

---

### 2. `GET /api/v1/shopify/callback`

| Case | Input | Expected |
|------|-------|----------|
| Valid callback | Valid `code`, `shop`, `state`, `hmac`, `timestamp` query params | 307 redirect to `{frontend_url}/dashboard/settings/integrations?connected=true` |
| Invalid HMAC | Tampered HMAC value | 400 `"Invalid HMAC signature"` |
| Expired/missing nonce | Valid HMAC but `state` not in Redis | 400 `"Invalid or expired state"` |
| Shop mismatch | Valid HMAC + valid nonce but `shop` differs from stored value | 400 `"Shop mismatch"` |
| Token exchange failure | Valid HMAC + nonce but Shopify returns 400 on code exchange | 500 (should be improved to 400 with message) |
| Upsert - new integration | No existing `StoreIntegration` for store | Creates new row with `platform=shopify`, `status=active`, encrypted `access_token` |
| Upsert - existing integration | Existing `StoreIntegration` for store | Updates existing row, resets `sync_error` to null |
| Celery task triggered | Successful callback | `sync_products_full.delay(str(store_id))` called |
| Webhook registration | Successful callback | `ShopifyClient.register_webhooks()` called (failure is non-fatal) |

**HMAC verification logic:**
1. Remove `hmac` key from query params.
2. Sort remaining params alphabetically.
3. URL-encode as `key=value&key=value`.
4. Compute `HMAC-SHA256` with `shopify_client_secret` as key.
5. Compare hex digest with received HMAC.

---

### 3. `POST /api/v1/shopify/disconnect`

| Case | Input | Expected |
|------|-------|----------|
| Valid disconnect | Auth header + `store_id` with active Shopify integration | 200 `{"status": "disconnected", "message": "Shopify store disconnected"}` |
| No integration found | Auth header + `store_id` with no Shopify integration | 404 `"No Shopify integration found"` |
| Unauthorized | No/invalid Bearer token | 401/403 |
| Wrong store | Valid auth but `store_id` belongs to another user | 403 (from `get_store_for_user`) |
| Credentials cleared | After disconnect | `integration.credentials` = `{}`, `status` = `disconnected` |
| Webhook cleanup | Active integration | `ShopifyClient.delete_webhooks()` called (failure is non-fatal) |

---

### 4. `POST /api/v1/shopify/sync`

| Case | Input | Expected |
|------|-------|----------|
| Valid sync trigger | Auth header + `store_id` with active integration | 200 `{"status": "syncing", "message": "Product sync started"}` |
| No active integration | Auth header + `store_id` with disconnected/missing integration | 404 `"No active Shopify integration"` |
| Celery task dispatched | Valid request | `sync_products_full.delay(str(store_id))` called |
| Unauthorized | No/invalid Bearer token | 401/403 |

---

### 5. `GET /api/v1/shopify/status`

| Case | Input | Expected |
|------|-------|----------|
| Connected store | Auth header + `store_id` with active Shopify integration | 200 with `platform="shopify"`, `status="active"`, `platform_domain`, `last_synced_at`, `product_count` |
| Disconnected store | Auth header + `store_id` with disconnected integration | 200 with `status="disconnected"` |
| No integration | Auth header + `store_id` with no integration at all | 200 with `status="disconnected"`, `platform_domain=""`, `product_count=0` |
| Product count accuracy | Store with N products in DB | `product_count` = N |
| Unauthorized | No/invalid Bearer token | 401/403 |

---

### 6. `GET /api/v1/products/`

| Case | Input | Expected |
|------|-------|----------|
| Paginated list | `store_id=<uuid>&page=1&page_size=10` | 200 with `items` array, each item has `id`, `title`, `description`, `handle`, `vendor`, `product_type`, `status`, `tags`, `variants`, `images`, `image_url`, `platform_product_id` |
| Page 2 | `page=2&page_size=5` | Returns next 5 items (or fewer if near end) |
| Empty store | `store_id` with no products | 200 with empty `items` array |
| Unauthorized | No/invalid Bearer token | 401/403 |

---

### 7. Webhook Endpoints (`/api/v1/webhooks/shopify/`)

#### `POST /products-create`

| Case | Input | Expected |
|------|-------|----------|
| Valid webhook | Valid HMAC in `X-Shopify-Hmac-Sha256` header + product JSON body + `X-Shopify-Shop-Domain` header | 200, triggers `sync_single_product` task |
| Invalid signature | Missing or wrong HMAC header | 401/403 `"Invalid webhook signature"` |
| Unknown shop | Valid HMAC but shop domain not in `store_integrations` | Appropriate error or no-op |

#### `POST /products-update`

| Case | Input | Expected |
|------|-------|----------|
| Valid webhook | Same as create | 200, triggers `sync_single_product` task |
| Invalid signature | Wrong HMAC | 401/403 |

#### `POST /products-delete`

| Case | Input | Expected |
|------|-------|----------|
| Valid webhook | Valid HMAC + `{"id": <product_id>}` body | 200, deletes product from DB |
| Invalid signature | Wrong HMAC | 401/403 |

**Webhook HMAC verification:**
- Compute `HMAC-SHA256` of raw request body using `shopify_client_secret`.
- Base64-encode the digest.
- Compare with `X-Shopify-Hmac-Sha256` header.

---

## Celery Task Tests

### 8. `sync_products_full`

| Case | Input | Expected |
|------|-------|----------|
| Full sync | `store_id` string | Fetches all products from Shopify API, upserts each into `products` table, updates `last_synced_at` on integration |
| Decrypts token | Task reads `credentials.access_token` | Successfully decrypts Fernet-encrypted token |
| Error handling | Shopify API returns error | Sets `integration.sync_error` with error message |
| Product count | Shopify store has N products | DB has N products after sync |

### 9. `sync_single_product`

| Case | Input | Expected |
|------|-------|----------|
| New product | Product data from webhook | Inserts new product row |
| Existing product | Product with matching `platform_product_id` | Updates existing row |

### 10. `generate_product_embeddings`

| Case | Input | Expected |
|------|-------|----------|
| Generate embeddings | `store_id` string | Generates vector embeddings for all products in store |

---

## Encryption Tests

### 11. `encrypt_token` / `decrypt_token`

| Case | Input | Expected |
|------|-------|----------|
| Round-trip | `encrypt_token("shpat_xxx")` then `decrypt_token(result)` | Returns `"shpat_xxx"` |
| Different inputs produce different outputs | Two different tokens | Different encrypted values |
| Invalid encrypted data | `decrypt_token("garbage")` | Raises `InvalidToken` or similar exception |

---

## OAuth Helper Tests

### 12. `verify_hmac`

| Case | Input | Expected |
|------|-------|----------|
| Valid HMAC | Params with correct HMAC computed from secret | Returns `True` |
| Tampered param | One param value changed after HMAC computation | Returns `False` |
| Missing HMAC key | Params without `hmac` key | Returns `False` (empty string comparison fails) |
| Extra params | Additional params not in original HMAC | Returns `False` |

### 13. `build_auth_url`

| Case | Input | Expected |
|------|-------|----------|
| Correct URL format | `shop="test.myshopify.com"`, `nonce="abc123"` | Returns `https://test.myshopify.com/admin/oauth/authorize?client_id=...&scope=...&redirect_uri=...&state=abc123` |
| Redirect URI | Any input | `redirect_uri` = `{settings.api_url}/api/v1/shopify/callback` |

### 14. `exchange_code_for_token`

| Case | Input | Expected |
|------|-------|----------|
| Successful exchange | Valid shop + code (mock Shopify response) | Returns access token string |
| Failed exchange | Shopify returns 400 | Raises `HTTPStatusError` |

---

## Frontend UI Tests

### 15. Integrations Page - Disconnected State

| Case | Expected |
|------|----------|
| Page renders | Shows "Shopify" card with "Not Connected" badge |
| Shop domain input | Text input with placeholder "mystore" and ".myshopify.com" suffix |
| Connect button | "Connect Shopify" button is present and enabled |
| Click connect | Navigates to `/api/v1/shopify/install?shop={input}.myshopify.com&store_id={store_id}` |

### 16. Integrations Page - Connected State

| Case | Expected |
|------|----------|
| Page renders | Shows "Connected" green badge |
| Store info | Displays `Store: {domain}`, `Products synced: {count}`, `Last sync: {datetime}` |
| Resync button | "Resync Products" button calls `POST /api/v1/shopify/sync` |
| Disconnect button | "Disconnect" button calls `POST /api/v1/shopify/disconnect`, UI reverts to disconnected state |
| Shopify Admin link | Opens `https://{domain}/admin` in new tab |

### 17. Products Page

| Case | Expected |
|------|----------|
| Products grid | Displays product cards in a 3-column grid |
| Product card | Shows image, title, price, vendor, status badge |
| Status badges | "active" = green/teal, "archived" = gray |
| Edit in Shopify link | Links to Shopify admin product page |
| Empty state | When no products synced, shows appropriate empty message |
| Pagination | If > page_size products, pagination controls appear |

### 18. Sidebar Navigation

| Case | Expected |
|------|----------|
| Products link | Visible in sidebar, navigates to `/dashboard/products` |
| Integrations link | Visible in sidebar, navigates to `/dashboard/settings/integrations` |

---

## Database Schema Validations

### 19. `store_integrations` Table

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PK, default uuid4 |
| `store_id` | UUID | FK to `stores.id`, unique, not null |
| `platform` | `platform_type` enum | Values: `shopify`, `woocommerce`, `bigcommerce`, `magento`, `custom` |
| `platform_store_id` | VARCHAR(255) | Not null |
| `platform_domain` | VARCHAR(255) | Not null, indexed |
| `credentials` | JSONB | Not null, default `{}` |
| `status` | `integration_status` enum | Values: `pending`, `active`, `disconnected`, `error` |
| `status_message` | TEXT | Nullable |
| `last_synced_at` | TIMESTAMP WITH TIME ZONE | Nullable |
| `sync_error` | TEXT | Nullable |

**Important:** PostgreSQL enum values must be **lowercase** (matching Python enum `.value`).

### 20. `products` Table

Verify products are stored with:
- `store_id` FK to `stores.id`
- `platform_product_id` (Shopify product ID as string)
- `title`, `description`, `handle`, `vendor`, `product_type`, `status`
- `variants` as JSONB array
- `images` as JSONB array
- `image_url` (first image src)
- `tags` as array

---

## Bugs Found During Manual Testing

| Bug | Root Cause | Fix |
|-----|-----------|-----|
| OAuth callback 500 on INSERT | Alembic migration created `platform_type` and `integration_status` enums with UPPERCASE values (`SHOPIFY`, `ACTIVE`), but Python model sends lowercase (`shopify`, `active`) | `ALTER TYPE ... RENAME VALUE` on live DB + fixed migration to use lowercase values |
| `/install` returns 401 | Endpoint had `CurrentUser` dependency requiring Bearer auth, but it's called via browser redirect (no token) | Removed auth dependencies from `/install`; security provided by nonce/state validation |
| Shopify "redirect_uri not whitelisted" | Shopify app on dev.shopify.com had ngrok URL configured | Updated app version redirect URL to `http://localhost:8000/api/v1/shopify/callback` |

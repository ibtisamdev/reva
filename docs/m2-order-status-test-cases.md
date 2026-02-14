# M2: Order Status Agent — Manual Test Cases

Edge-case-focused test cases for the Order Status Agent. Each case targets a specific code path or integration seam.

**Key source files:**
- `app/services/order_service.py` — verification, caching, status messages
- `app/services/order_tools.py` — LangChain tool definitions
- `app/services/chat_service.py` — orchestration, tool loop, inquiry recording
- `app/services/graph/nodes.py` — support_node (order intent handler)
- `app/services/graph/prompts.py` — SUPPORT_NODE_PROMPT with order instructions

---

## 1. Verification & Identity

These test the identity verification firewall — the customer must prove ownership before seeing any order data.

| ID | Case | Action | Expected | Code Path |
|----|------|--------|----------|-----------|
| TC-M2-01 | Email case sensitivity | Send: "My order is #1001, email is JohnDoe@GMAIL.COM" | Verification succeeds. Email comparison is case-insensitive. | `order_service.py:77` — `order_email.lower() != email.lower()` |
| TC-M2-02a | Order number with `#` prefix | Send order number as "#1001" | `#` stripped for cache key. Shopify lookup succeeds. | `order_service.py:59` — `order_number.lstrip('#')` |
| TC-M2-02b | Order number without prefix | Send order number as "1001" | Works directly. | Same path, `lstrip('#')` is a no-op. |
| TC-M2-02c | Order number in natural language | Send: "order 1001" | Depends on LLM extracting "1001" as the `order_number` arg. Observe what the tool receives. | LLM arg extraction → `VerifyCustomerInput` |
| TC-M2-02d | Zero-padded order number | Send: "#001001" | May or may not match Shopify depending on how Shopify stores display numbers. Observe behavior. | `order_service.py:66` — `client.get_order_by_number()` |
| TC-M2-02e | Non-Shopify format | Send: "ORD-1001" | Shopify API returns no order. "Order not found." | `order_service.py:68-71` |
| TC-M2-03 | Correct order, wrong email | Provide a real order number with a non-matching email | "The email address does not match our records for this order." **No order details leaked.** | `order_service.py:76-80` — email check AFTER fetch |
| TC-M2-04 | Wrong order, correct email | Provide a nonexistent order number with a valid email | "Order not found. Please check the order number and try again." | `order_service.py:66-71` — Shopify returns nothing |
| TC-M2-05 | Order number only (no email) | Send: "Where is my order #1001?" | Agent asks for email **before** calling verify tool. Must NOT call `verify_customer_and_lookup_order` with missing email. | Prompt compliance: SUPPORT_NODE_PROMPT says "MUST ask for BOTH" |
| TC-M2-06 | Email only (no order number) | Send: "My email is john@test.com, can you check my order?" | Agent asks for order number. | Mirror of TC-M2-05 |
| TC-M2-07 | Both provided in one message | Send: "Check order 1042, email sarah@example.com" | Agent extracts both args, calls verify tool immediately, returns order status. | LLM arg extraction → tool call → `verify_and_lookup()` |
| TC-M2-08 | Repeated failure then success | 1. Wrong email → fail. 2. Wrong email → fail. 3. Correct email → success. | Each attempt is independent. 3rd attempt succeeds. `OrderInquiry` records: 2× `VERIFICATION_FAILED`, 1× `ANSWERED`. | No lockout mechanism. State doesn't poison between attempts. |

**Notes:**
- TC-M2-03 is a **security-critical** test. Order data is fetched and cached on the first attempt, but the email mismatch must prevent it from being returned.
- TC-M2-05/06 test **prompt compliance** — the LLM must follow the instruction to collect both fields before calling the tool. If it doesn't, the tool will be called with incomplete data.

---

## 2. Order Status Scenarios

These test every branch of `_get_status_message()` in `order_service.py:207-254`. Each requires a real (or mocked) Shopify order in the corresponding state.

| ID | Case | Shopify State | Expected Status Message | Code Path |
|----|------|---------------|-------------------------|-----------|
| TC-M2-09 | Paid, unfulfilled | `financial_status=paid`, `fulfillment_status=null` | "Your order has been confirmed and is being prepared for shipment." | `order_service.py:226-227` |
| TC-M2-10 | Partially fulfilled | `fulfillment_status=partial`, 2 fulfillments | "Your order has been partially shipped (2 shipments so far)." Check: pluralization correct for 1 vs 2+. | `order_service.py:234-239` |
| TC-M2-11 | Fully fulfilled with tracking | `fulfillment_status=fulfilled`, tracking_number + carrier present | "Your order has been shipped via [carrier]. Tracking number: [number]" | `order_service.py:241-251` — uses `fulfillments[-1]` (last) |
| TC-M2-12 | Fulfilled, NO tracking | `fulfillment_status=fulfilled`, `tracking_number=null` | "Your order has been shipped." (no tracking mentioned) | `order_service.py:252` — fallback when no tracking |
| TC-M2-13 | Cancelled | `cancelled_at` is set (any financial/fulfillment status) | "This order has been cancelled." **Takes priority over all other statuses.** | `order_service.py:215-216` — checked first |
| TC-M2-14 | Fully refunded | `financial_status=refunded` | "This order has been fully refunded." | `order_service.py:218-219` |
| TC-M2-15 | Partially refunded | `financial_status=partially_refunded` | "This order has been partially refunded." | `order_service.py:221-222` |
| TC-M2-16 | Payment pending | `financial_status=pending`, `fulfillment_status=null` | "Your order is awaiting payment confirmation." | `order_service.py:228-229` |

**Notes:**
- TC-M2-13 is important: cancellation takes priority. Even if `financial_status=paid` and `fulfillment_status=fulfilled`, cancelled_at being set means the message says "cancelled."
- TC-M2-10: check the pluralization — "1 shipment" vs "2 shipments so far."
- TC-M2-11: the code uses `fulfillments[-1]` — only the **last** fulfillment's tracking is shown. If a customer has multiple shipments, they only see the latest tracking number in the status message.

---

## 3. Follow-up Queries & Conversation Continuity

These test multi-turn order conversations and history reconstruction.

| ID | Case | Steps | Expected | Why It Matters |
|----|------|-------|----------|----------------|
| TC-M2-17 | Same-order follow-up | 1. Verify order #1001 successfully. 2. Ask "What's the tracking number?" | Agent uses `lookup_order_status` or `get_tracking_details` — NOT `verify_customer_and_lookup_order` again. Uses cached data. | Prompt says "use `lookup_order_status` for follow-up questions." Re-verification wastes API calls and is bad UX. |
| TC-M2-18 | Different-order follow-up | 1. Verify order #1001 with email A. 2. Ask "Can you also check order #1002?" | Agent asks for email for #1002. Does NOT assume same email. | Different orders may belong to different customers. Agent must not skip verification. |
| TC-M2-19 | History reconstruction with tool calls | 1. Complete full order verification flow. 2. Send a follow-up message. | Conversation history correctly reconstructs `AIMessage(tool_calls=[...])` + `ToolMessage` pairs. Agent understands prior verification context. | `chat_service.py:322-350` — if tool_calls/tool_results aren't re-hydrated properly, LangChain throws validation errors or LLM loses context. |

**Notes:**
- TC-M2-19 is a **critical integration test**. The DB stores `tool_calls` and `tool_results` as JSON. On the next turn, these are reconstructed into LangChain message objects. Any mismatch in `tool_call_id` between `AIMessage.tool_calls` and `ToolMessage.tool_call_id` will cause errors.

---

## 4. Infrastructure Edge Cases

These test behavior when dependencies are unavailable or in edge states.

| ID | Case | Setup | Expected | Code Path |
|----|------|-------|----------|-----------|
| TC-M2-20 | Redis unavailable | Stop Redis or make it unreachable | `order_tools = None` (creation fails silently). Chat still works. Agent cannot call order tools — responds that order lookup isn't available or asks user to try later. | `chat_service.py:118-127` — try/except around order tool creation |
| TC-M2-21 | No Shopify integration | Use a store with no active `StoreIntegration` record | "Order lookup is not available for this store." | `order_service.py:52-56` — `_get_shopify_client()` returns None |
| TC-M2-22 | Token decryption failure | Corrupt the encrypted `access_token` in `StoreIntegration.credentials` | Same behavior as no integration — client creation fails silently, returns None. | `order_service.py:138-143` — decrypt_token exception caught |
| TC-M2-23 | Redis cache lifecycle | 1. Look up order (cache miss → Shopify API hit). 2. Look up same order within 15 min (cache hit). 3. Wait 15+ min, look up again (cache expired → Shopify API). | First and third calls hit Shopify. Second uses cache. All return same data. | `ORDER_CACHE_TTL = 900` (15 min). `order_service.py:59-73` |
| TC-M2-24 | OrderInquiry DB recording | Complete a successful verification. Query `order_inquiries` table. | Record exists with correct `store_id`, `conversation_id`, `customer_email`, `order_number`, `inquiry_type=ORDER_STATUS`, `resolution=ANSWERED`, `order_status`, `fulfillment_status`. | `chat_service.py:392-432` — `_maybe_record_order_inquiry()` |

**Notes:**
- TC-M2-20: When Redis is down, the agent has NO order tools. The LangGraph still routes `order_status` intent to `support_node`, but `support_node` runs without tools. The LLM should explain that order lookup isn't currently available rather than crashing.
- TC-M2-24: Also test a **failed** verification — the `OrderInquiry` should have `resolution=VERIFICATION_FAILED` and `order_status=None`.

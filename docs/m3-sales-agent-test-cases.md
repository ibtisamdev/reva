# M3: Sales & Recommendation Agent — Manual Test Cases

Edge-case-focused test cases for the LangGraph Sales Agent, product search, recommendations, and combined M2+M3 flows.

**Key source files:**
- `app/services/graph/workflow.py` — LangGraph graph definition
- `app/services/graph/nodes.py` — classify_intent, search_node, recommend_node, support_node, general_node, clarify_node
- `app/services/graph/router.py` — route_conversation (CLARIFY_THRESHOLD = 0.6)
- `app/services/graph/prompts.py` — all node prompts with grounding rules
- `app/services/graph/state.py` — ConversationState TypedDict
- `app/services/search_service.py` — hybrid search (vector + fulltext + RRF)
- `app/services/recommendation_service.py` — similar, upsell, cross-sell, compare
- `app/services/tools/product_tools.py` — 6 LangChain product tools
- `app/services/chat_service.py` — orchestration, product card extraction

**Architecture overview:**
```
User message → classify_intent → route_conversation → [search|recommend|support|general|clarify] → END
```

---

## 1. Intent Classification & Routing

Tests the intent classifier (GPT-4o, temp=0.0) and the conditional router.

| ID | Case | Message | Expected Route | Why It Matters |
|----|------|---------|----------------|----------------|
| TC-M3-01 | Ambiguous: order + search | "I bought a red dress last week but I'd like to see if you have it in blue" | Could go to `search` or `support`. Either route should produce a useful response. | Blends order context with product search. Tests classifier on multi-intent messages. |
| TC-M3-02 | Ambiguous: complaint + order | "My tracking says delivered but I never received it" | Routes to `support` (order_status or complaint both map to support). Should ask for order# + email. | Both `order_status` and `complaint` map to `support_node`, so the route is correct either way. Watch how the agent frames it. |
| TC-M3-03 | Low confidence → clarify | Send: "hmm" or "stuff" or "blah" | Confidence < 0.6 → routes to `clarify`. Agent asks ONE question, < 15 words, no category suggestions. | Tests `CLARIFY_THRESHOLD = 0.6` in `router.py:21` and clarify node prompt constraints. |
| TC-M3-04 | Small talk (no products) | "Hey, how are you?" | Routes to `general`. Friendly 1-2 sentence response. NO product suggestions. NO "How can I help you?" | General prompt says "Do NOT ask follow-up questions" and no product mentions unless in context. |
| TC-M3-05 | Complaint | "This is terrible, I want my money back, the product broke after one day" | Routes to `support` (complaint → support). Responds empathetically. May ask for order info. | Complaint is a distinct intent but maps to same node as order_status. Tests tone handling. |
| TC-M3-06 | FAQ / policy question | "What's your return policy?" | Routes to `support` (faq_support → support). Uses RAG context. Does NOT hallucinate a policy. | If no KB docs match, agent should say it doesn't have that info. |
| TC-M3-07 | Intent switching mid-conversation | 1. "Show me running shoes" (search) → 2. "Where's my order #1001?" (support) → 3. "Show me those shoes again" (search) | Each message independently classified. Graph runs fresh per turn. History provides context but intent re-classified. | LangGraph is stateless between turns. Tests that switching doesn't cause confusion. |
| TC-M3-08 | Vague with no actionable content | "I need something" | Low confidence → `clarify`. Asks what type of product. | Tests classifier identifying insufficient info. |

**Notes:**
- Intent classification uses `temperature=0.0` for determinism, but identical messages can still classify differently across runs.
- The classifier returns JSON: `{"intent": "...", "confidence": 0.0-1.0}`. Markdown wrapping is stripped (`nodes.py:149-150`).

---

## 2. Product Search

Tests `search_node` with `force_first_tool_call=True`, the `SearchService` hybrid search, and filter handling.

| ID | Case | Message | Expected | Code Path |
|----|------|---------|----------|-----------|
| TC-M3-09 | Basic search | "Show me snowboards" | `search_products` called IMMEDIATELY (no questions first). Text response is a **brief conversational summary** — NOT listing individual product names/prices. Product cards in `products` array contain details. | `force_first_tool_call=True` in `nodes.py:182`. Updated prompt: "product cards handle display." |
| TC-M3-10 | Price filter (max) | "Running shoes under $100" | Tool called with `price_max=100`. Only products ≤ $100 in results. | LLM extracts price → `SearchProductsInput.price_max` |
| TC-M3-11 | Price filter (range) | "Jackets between $200 and $500" | Tool called with `price_min=200`, `price_max=500`. Results within range. | Both min and max in `_apply_filters()` |
| TC-M3-12 | Zero results + grounding | "Do you have helicopter parts?" | "No products found" or similar. Agent does NOT suggest what the store might carry. | Grounding rule: "Do NOT suggest product categories that might exist." |
| TC-M3-13 | Vague search (still searches) | "Something nice for a birthday gift" | Tool called immediately with "birthday gift" or similar. Whatever results come back are presented. | `force_first_tool_call=True` — even vague queries trigger search, not clarification. |
| TC-M3-14 | Stock filter default | "What do you have in stock?" | `in_stock_only=True` (default). Only shows available products. | `SearchProductsInput.in_stock_only` defaults to `True` |
| TC-M3-15 | Hybrid search (semantic + keyword) | Search "comfy shoes" in store with "cushioned sneakers" (semantic) and "comfort shoes" (keyword) | Both appear in results. RRF combines rankings. | `search_service.py:49-51` — RRF fusion of vector + fulltext |
| TC-M3-16 | Embedding service down | Disable/break OpenAI embeddings API | Vector search returns `[]` (exception caught). Full-text search still works. Partial results returned. | `search_service.py:62-65` — try/except on embedding generation |
| TC-M3-17 | Special characters in search | "SKU-12345" or "product #42" | `plainto_tsquery` handles safely. No SQL injection. Results based on text match. | `search_service.py:111` — `plainto_tsquery` for robustness |
| TC-M3-18 | Price filter on no-variant product | Search with price filter; store has products with empty `variants` array | Products with no variants excluded from results (price expression evaluates to null). | `_apply_filters` — `Product.variants[0]["price"]` on empty JSONB array |

**Notes:**
- TC-M3-09: The updated prompt now says "Do NOT list individual product names, prices, or descriptions — the product cards handle this automatically." Verify the LLM follows this.
- TC-M3-15: RRF score = `1/(K + rank + 1)` where `K=60`. Products appearing in both vector and fulltext results get higher combined scores.
- TC-M3-16: This is a **graceful degradation** test. When only fulltext works, results are keyword-only (no semantic matching).

---

## 3. Product Recommendations

Tests `recommend_node` with `force_first_tool_call=True` and the `RecommendationService`.

| ID | Case | Action | Expected | Code Path |
|----|------|--------|----------|-----------|
| TC-M3-19 | Similar products | After search, say: "Show me something similar to [product name]" | Routes to `recommend_node`. Uses `get_similar_products`. Returns products ranked by embedding similarity. | `recommendation_service.py:24-65` — cosine distance |
| TC-M3-20 | Similar — source has no embedding | Request similar products for a product with `embedding=null` | Returns empty list gracefully: "No similar products found." | `recommendation_service.py:42` — early return |
| TC-M3-21 | Upsell price range | Request alternatives for a $50 product | `suggest_alternatives` returns upsells at $55-$65 (10-30% higher, same category) + cross-sells (different category, overlapping tags). | `recommendation_service.py:91-92` — `price * 1.10` to `price * 1.30` |
| TC-M3-22 | Upsell — source has no price | Request upsells for product with no variants/pricing | Empty upsell list (no error). Cross-sells may still work if tags exist. | `recommendation_service.py:88-89` — `_extract_price()` returns None |
| TC-M3-23 | Cross-sell — source has no tags | Request cross-sells for product with `tags=[]` or `tags=null` | Returns empty list. | `recommendation_service.py:135` — `not source.tags` early return |
| TC-M3-24 | Cross-sell — source has no product_type | Request cross-sells for product where `product_type=null` | Returns products with overlapping tags but **without** "different product type" filter. Same-type products may appear. | `recommendation_service.py:147` — condition only added when `source.product_type` exists |
| TC-M3-25 | Compare products | "Compare [product A] and [product B]" | Routes to `recommend_node`. `compare_products` called. Side-by-side comparison with pricing, variants, availability. | `recommendation_service.py:156-213` |
| TC-M3-26 | Compare — invalid UUID | LLM passes a garbage product ID | `UUID(product_id)` throws `ValueError`. Tool should return error, not crash the entire request. | `product_tools.py:277` — `UUID(pid)` parsing |
| TC-M3-27 | Compare — cross-store IDs | Pass a product ID from store B while chatting with store A | Product from store B NOT found (scoped by `store_id`). Comparison shows only store A's product or error. | `Product.store_id == store_id` filter in `compare_products` |

**Notes:**
- TC-M3-21: Upsell logic requires BOTH same category/vendor AND 10-30% higher price. If the source has `product_type`, it filters by type. If not, it falls back to `vendor`. If neither exists, no upsells are returned.
- TC-M3-24: This is a subtle edge case. Without `product_type` on the source, the "different type" filter is skipped, so cross-sells may include same-type products — which is not ideal but not a bug per se.
- TC-M3-26: The `UUID()` call is NOT wrapped in try/except in the tool. The tool loop's exception handler (`nodes.py:116-118`) catches it, but the tool returns `f"Error: {e}"` which is not ideal UX.

---

## 4. Tool Forcing & LLM Behavior

Tests that `force_first_tool_call=True` works correctly and fallback behavior.

| ID | Case | Action | Expected | Code Path |
|----|------|--------|----------|-----------|
| TC-M3-28 | Search never asks first | "I might need some shoes, not sure though" | Agent searches immediately. Does NOT say "Would you like me to search?" or "What kind of shoes?" | `tool_choice="required"` on first iteration (`nodes.py:82-83`) + prompt |
| TC-M3-29 | Recommend never asks first | "What else do you have like that first product?" | Agent calls a tool immediately. Does NOT ask "Which product would you like similar items for?" | Same `force_first_tool_call=True` in recommend_node |
| TC-M3-30 | Tool loop exhaustion | Trigger a scenario where the agent makes 3 tool calls without generating a text response (hard to trigger manually) | Returns: "I'm having trouble processing your request. Please try again." | `nodes.py:128` — fallback after `MAX_TOOL_ITERATIONS = 3` |
| TC-M3-31 | No product tools available | Product tool creation fails (e.g., missing services) | Chat still works. search_node runs without tools, generates text-only response. No crash. | `nodes.py:181-186` — `if tools:` guard. Without tools, does plain LLM completion. |

**Notes:**
- TC-M3-28/29: `tool_choice="required"` forces the LLM to call a tool on the first iteration. On subsequent iterations, `tool_choice` is not set (auto), allowing the LLM to respond with text after seeing tool results.
- TC-M3-30: This is nearly impossible to trigger manually since the LLM usually generates text after seeing tool results. It's a safety net.

---

## 5. Grounding & Hallucination Prevention

Tests that the agent ONLY mentions products from tool results/context and never invents information.

| ID | Case | Action | Expected | Prompt Rule |
|----|------|--------|----------|-------------|
| TC-M3-62 | Search text should not list product details | "Show me necklaces" | Text says something like "Here are some necklaces I found:" — does NOT list individual product names, prices, or descriptions. Product cards handle display. | "Do NOT list individual product names, prices, or descriptions — the product cards handle this automatically." |
| TC-M3-32 | No invented products | Search returns 3 products. Read the text response carefully. | All mentioned products come from tool results or context. No fictional products. | "Only present products returned by the search_products tool" |
| TC-M3-33 | No suggested categories after empty search | Search returns zero results. | Agent says "We don't carry that" or similar. Does NOT say "But we have shoes, jackets, accessories..." | "Do NOT suggest product categories from general knowledge" |
| TC-M3-34 | Clarify node doesn't list categories | Message triggers clarify node. | Agent asks "What type of product are you looking for?" — NOT "Are you looking for shoes, jackets, or accessories?" | Clarify prompt: "Do NOT suggest product categories from general knowledge" |
| TC-M3-35 | General node doesn't push products | "Thanks, have a good day!" | Friendly goodbye. Does NOT say "Before you go, check out our new [product]!" | General prompt: "never reference specific products" |

**Notes:**
- Grounding is critical for e-commerce. Recommending a product that doesn't exist in the store is worse than recommending nothing.
- TC-M3-62 is NEW — tests the updated prompt that delegates product display to frontend product cards.

---

## 6. Multi-Turn Conversation Edge Cases

Tests conversation history management, truncation, and state.

| ID | Case | Steps | Expected | Code Path |
|----|------|-------|----------|-----------|
| TC-M3-36 | Long history truncation | Have a 20+ message conversation. Send another message. | Only last 10 messages in context. Agent still responds coherently despite missing early context. | `MAX_CONVERSATION_HISTORY = 10` in `chat_service.py:35` |
| TC-M3-37 | Interleaved tool calls in history | 1. Search (tool_calls). 2. Order lookup (different tool_calls). 3. Search again. | History reconstructs properly: `AIMessage(tool_calls=[...])` + `ToolMessage` pairs. No orphaned ToolMessages. | `chat_service.py:322-350` — reconstruction loop |
| TC-M3-38 | New conversation (no ID) | Send message with no `conversation_id`. | New conversation created. `session_id` generated. Response works. | `_get_or_create_conversation` create path |
| TC-M3-39 | Invalid conversation_id | Send with a random UUID. | Conversation not found → new one created silently. | Falls through `_get_or_create_conversation` |
| TC-M3-40 | conversation_id from wrong store | Use a conversation_id belonging to store B while chatting with store A. | Not found (scoped by `store_id`). New conversation created for store A. | `Conversation.store_id == store_id` filter |

**Notes:**
- TC-M3-37 is the most fragile. If `tool_call_id` in the stored `tool_results` doesn't match the `tool_calls` in the reconstructed `AIMessage`, LangChain will throw validation errors.

---

## 7. RAG Context & Retrieval Integration

Tests how RAG context interacts with the LangGraph workflow.

| ID | Case | Setup | Expected | Code Path |
|----|------|-------|----------|-----------|
| TC-M3-41 | RAG retrieval fails entirely | Break embedding/retrieval service. | Chat still works. `chunks = []`, `products = []`. Agent responds via tools only, no KB context. | `chat_service.py:95-115` — try/except on retrieval |
| TC-M3-42 | KB has answer for FAQ | Ask a question that's in the knowledge base. | Agent uses RAG context (passed as `context_text` to support_node). Does NOT hallucinate. | `support_node` uses `context_text` from RAG |
| TC-M3-43 | RAG products vs tool products | Both RAG product_context and product_tools available. | Search/recommend intents use tools. RAG product context is supplementary (in `context_section`). Support uses RAG directly. | Dual-source product info flow |

---

## 8. API Response & Product Cards

Tests the `ChatResponse` format including the new `products` field with `ProductCard` objects.

| ID | Case | Action | Expected | Code Path |
|----|------|--------|----------|-----------|
| TC-M3-44 | Sources from KB | Ask question that uses RAG context. | `ChatResponse.sources` is a non-empty array with citation info. | `citation_service.create_sources_from_chunks(chunks)` |
| TC-M3-45 | No sources available | Ask something with no RAG match. | `sources` is `[]` (empty array), not `null`. | Empty chunks → empty sources |
| TC-M3-46 | Token usage | Check `tokens_used` in saved message. | Currently `0` (hardcoded). Graph makes multiple LLM calls; individual counts not tracked. | `chat_service.py:383` — `tokens_used = 0` |
| TC-M3-59 | Product cards from search | Search for products. | `ChatResponse.products` contains `ProductCard` objects with `product_id`, `title`, `price`, `image_url`, `in_stock`. | `extract_products_from_tool_results` — parses `{"results": [...]}` |
| TC-M3-60 | Product cards from alternatives | Request alternatives (`suggest_alternatives`). | `products` array contains cards from BOTH `upsells` and `cross_sells`, deduplicated. | Extracts from both `upsells` and `cross_sells` keys |
| TC-M3-61 | Product card deduplication | Scenario where `search_products` and `get_similar_products` return overlapping products. | Each product appears only ONCE in `products` array. | `seen_ids` set in `extract_products_from_tool_results` |

**Notes:**
- TC-M3-59/60/61: The `extract_products_from_tool_results` function (`chat_service.py:47-101`) handles all tool result shapes:
  - `search_products` / `get_similar_products`: `{"results": [...]}`
  - `compare_products`: `{"products": [...]}`
  - `suggest_alternatives`: `{"upsells": [...], "cross_sells": [...]}`
- Deduplication is by `product_id`. If the same product appears from two different tools, it only shows up once.

---

## 9. Multi-Tenant Isolation

Critical security tests ensuring stores cannot access each other's data.

| ID | Case | Action | Expected | Code Path |
|----|------|--------|----------|-----------|
| TC-M3-47 | Cross-store product search | Search in Store B for products only in Store A. | Zero results. All queries scoped by `store_id`. | `Product.store_id == store_id` in every SearchService query |
| TC-M3-48 | Cross-store order access | Verify Store A's order from Store B's widget. | Order not found. Shopify client is per-store. | `_get_shopify_client(store_id)` uses per-store credentials |
| TC-M3-49 | Tool store scoping | Verify that tools close over the correct `store_id`. | All tool queries use the requesting store's ID, not another store's. | Factory pattern: `create_product_tools(service, store_id)` with closures |

**Notes:**
- These are **security-critical**. A failure here means data leakage between tenants.
- The factory pattern (closures over `store_id`) is used consistently for both order tools and product tools.

---

## 10. Error Handling & Edge Cases

Tests resilience to unexpected inputs and service failures.

| ID | Case | Setup/Action | Expected | Code Path |
|----|------|--------------|----------|-----------|
| TC-M3-50 | OpenAI API failure | Invalid/rate-limited OpenAI key. | HTTPException 503: "AI service is temporarily unavailable. Please try again." | `chat_service.py:161-166` — catch-all exception handler |
| TC-M3-51 | Malformed classifier JSON | GPT-4o returns "I think the intent is search" instead of JSON. | Defaults to `intent="small_talk"`, `confidence=0.3` → routes to `clarify` (0.3 < 0.6). | `nodes.py:157-160` — JSONDecodeError fallback |
| TC-M3-52 | Unknown intent from classifier | GPT-4o returns `{"intent": "purchase", "confidence": 0.9}`. | `intent_to_node.get("purchase", "general")` → routes to `general`. | `router.py:33` — default fallback |
| TC-M3-53 | Empty user message | Send empty string or whitespace. | Handled gracefully. Likely low confidence → clarify. | `_get_last_human_message` returns "" for empty content |
| TC-M3-54 | Very long message (4000+ chars) | Send a wall of text. | Works but may hit token limits. Classifier has `max_tokens=100`, response has `max_tokens=800`. | Token budget limits on LLM calls |
| TC-M3-55 | tool_calls_record None vs empty | Send message that doesn't trigger any tools (e.g., "hi"). | `tool_calls_record` is `None` (not `[]`). | `chat_service.py:388` — converts `[]` to `None` |

**Notes:**
- TC-M3-51: The markdown stripping (`nodes.py:149-150`) handles GPT-4o wrapping JSON in ` ```json ``` `. But if the response is completely non-JSON, the fallback kicks in.
- TC-M3-52: Any intent not in `intent_to_node` maps to `"general"`. This prevents crashes from unexpected classifier outputs.

---

## 11. Widget-Specific Edge Cases

Tests behavior specific to the chat widget integration.

| ID | Case | Action | Expected | Code Path |
|----|------|--------|----------|-----------|
| TC-M3-56 | Rapid-fire messages | Send 5 messages in quick succession. | Each processed independently. No race conditions. Conversations don't corrupt. | Each request creates own ChatService instance |
| TC-M3-57 | Session continuity | 1. Open widget, send message, note `conversation_id`. 2. Send another message with same `conversation_id`. | Same conversation used. History maintained. | `_get_or_create_conversation` lookup path |
| TC-M3-58 | Context metadata | Send with `context: {"page": "/products/shoe-123", "referrer": "google"}`. | Context stored in `Conversation.extra_data`. Accessible for analytics. | `_get_or_create_conversation` — `extra_data=context` |

---

## 12. Combined M2+M3 Integration Flows

The most important tests — real-world scenarios crossing milestone boundaries.

| ID | Case | Steps | Expected | Why It Matters |
|----|------|-------|----------|----------------|
| TC-INT-01 | Search → Order inquiry | 1. "Show me winter jackets" (search). 2. "Can you check on my order #1001? Email: test@test.com" (order). | Search works. Then intent switches to support. Verification works. Both flows complete in one conversation. | Tests M3 → M2 transition in same conversation. |
| TC-INT-02 | Order → Search | 1. "Where's my order #1001? Email: john@test.com" (order). 2. "Thanks. Show me boots under $200?" (search). | Order verified. Then search works independently. Agent doesn't try to re-verify. | Tests M2 → M3 transition. |
| TC-INT-03 | Complaint needing both tools | "I received the wrong item in order #1001. My email is test@test.com. Can you show me what I was supposed to get?" | Complex multi-intent. Ideally verifies order, then uses product tools to look up correct items. May require multiple turns. | Hardest real-world scenario. M2 and M3 need to work together. |
| TC-INT-04 | Full conversation journey | 1. "Hi!" (general) → 2. "Show me running shoes" (search) → 3. "Similar to the first one?" (recommend) → 4. "Compare those two" (recommend) → 5. "Where's my order #1001? Email: x@y.com" (support) → 6. "Return policy?" (support) → 7. "Thanks bye!" (general) | Each step routes correctly. Accumulated history doesn't confuse classifier. All tools work. | End-to-end covering every intent. Tests history accumulation over many turns. |
| TC-INT-05 | Empty store (no integration, no products) | Chat with a brand new store. No Shopify integration. No synced products. | Order tools = None. Product tools exist but return empty. Agent still responds helpfully. No crashes. | Tests the absolute minimum viable state. |

**Notes:**
- TC-INT-03: This is the hardest test. The agent needs to: (a) classify as complaint/order_status, (b) verify the order, (c) look at line items, (d) potentially search for the correct product. The current single-intent-per-turn architecture means this likely takes 2-3 turns.
- TC-INT-04: This is a **soak test** for conversation history. By step 7, the history includes tool calls from search, recommendation, and order tools. The classifier must not be confused by this rich history.
- TC-INT-05: This verifies the system doesn't crash when it has nothing to work with — no data, no integrations, just the LLM and prompts.

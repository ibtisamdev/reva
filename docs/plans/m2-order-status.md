# Milestone 2: Order Status Agent - Implementation Plan

> **Status:** Not Started  
> **Timeline:** 3 weeks  
> **Goal:** Answer "Where is my order?" — the #1 support question (30-50% of all tickets).

---

## Overview

Milestone 2 builds on M1's foundation to handle order status inquiries. This milestone introduces customer verification, Shopify order lookup, and shipping carrier integrations to provide real-time order tracking information.

### Success Criteria

- [ ] Customer can verify identity using order number + email
- [ ] Agent can lookup orders from Shopify API
- [ ] Tracking information from Shopify fulfillments (tracking numbers, URLs, carrier names)
- [ ] Secure order details sharing with proper verification
- [ ] Multi-order support for customers with order history
- [ ] Order timeline showing full journey from purchase to delivery
- [ ] Magic link authentication for enhanced security (optional)
- [ ] WISMO (Where Is My Order) analytics dashboard

### Success Metrics

| Metric                             | Target       |
| ---------------------------------- | ------------ |
| Order lookup success rate          | > 95%        |
| Customer verification accuracy     | > 99%        |
| Tracking data freshness            | < 30 minutes |
| Response time for order queries    | < 2 seconds  |
| False positive rate (wrong orders) | < 0.1%       |

---

## Implementation Phases

M2 is broken into 3 sequential phases:

| Phase                                                 | Focus                          | Duration | Status      |
| ----------------------------------------------------- | ------------------------------ | -------- | ----------- |
| [Phase 1](m2-phases/phase-1-customer-verification.md) | Customer Verification & Lookup | 1 week   | Not Started |
| [Phase 2](m2-phases/phase-2-shipping-integration.md)  | Carrier Tracking Integration   | 1 week   | Not Started |
| [Phase 3](m2-phases/phase-3-dashboard-analytics.md)   | WISMO Dashboard & Analytics    | 1 week   | Not Started |

### Why This Order?

1. **Phase 1 (Verification)** - Build secure order lookup foundation with Shopify integration.
2. **Phase 2 (Tracking)** - Add real-time tracking data from shipping carriers.
3. **Phase 3 (Analytics)** - Provide merchants with WISMO insights and dashboard features.

This order allows for:

- Secure foundation before adding external integrations
- Core functionality working before analytics layer
- Incremental value delivery (basic order status → enhanced tracking → insights)

---

## Architecture

```
Widget                API                    Services                 External
  |                    |                        |                        |
  | POST /chat/messages|                        |                        |
  |------------------>|                        |                        |
  |                    | verify_customer()      |                        |
  |                    |----------------------->|                        |
  |                    |                        | Shopify Orders API     |
  |                    |                        | (orders + fulfillments)|
  |                    |                        |----------------------->|
  |                    |                        |<-----------------------|
  |                    |<-----------------------|                        |
  |                    | generate_response()    |                        |
  |                    |----------------------->|                        |
  |                    |                        | OpenAI + Order Context |
  |                    |                        |----------------------->|
  |                    |                        |<-----------------------|
  |                    |<-----------------------|                        |
  |<------------------|                        |                        |
```

### Key Components

| Component             | Location                       | Purpose                       |
| --------------------- | ------------------------------ | ----------------------------- |
| Customer Verification | `app/services/verification.py` | Secure identity validation    |
| Order Lookup Service  | `app/services/orders.py`       | Shopify order retrieval       |
| Tracking Service      | `app/services/tracking.py`     | Shopify fulfillment tracking data |
| Order Tools           | `app/tools/order_tools.py`     | LangChain tools for order ops |
| WISMO Analytics       | `app/services/analytics.py`    | Order status insights         |
| Magic Link Auth       | `app/services/auth_links.py`   | Secure email authentication   |

---

## Technical Decisions

| Decision              | Choice                     | Rationale                           |
| --------------------- | -------------------------- | ----------------------------------- |
| Customer Verification | Order Number + Email Match | Balance security with UX simplicity |
| Tracking Provider     | Shopify Fulfillments API   | Already available from order data, no external dependency |
| Tool Framework        | LangChain Tools            | Structured LLM tool calling         |
| Order Caching         | Redis (15 min TTL)         | Reduce Shopify API calls            |
| Magic Links           | JWT tokens (1 hour expiry) | Secure, stateless authentication    |

---

## Security Model

### Customer Verification Options

**Option A: Order Number + Email Match (Primary)**

```
Customer provides: Order #1234 + john@email.com
System validates: Does order #1234 belong to john@email.com?
If match → Show order details
If no match → "I couldn't find that order"
```

**Option B: Magic Link (Enhanced Security)**

```
Customer provides email → System sends secure link
Customer clicks → Authenticated session with full order history
```

**Option C: Logged-In Customer**

```
Widget inherits store authentication
Full access to customer's order history
```

### Order Status Mapping

| Shopify Status | Customer Message                             |
| -------------- | -------------------------------------------- |
| `pending`      | "Your order is confirmed and being prepared" |
| `paid`         | "Order received! We're packing it now"       |
| `fulfilled`    | "Your order has shipped!" + tracking         |
| `refunded`     | "This order has been refunded"               |

---

## Dependencies

### External Services

- Shopify Admin API (Orders, Fulfillments — includes tracking numbers, URLs, carrier names)
- OpenAI API (enhanced with order context)
- Redis (order caching)

### Internal Prerequisites

- M1 complete (RAG pipeline, chat service)
- Shopify OAuth integration from M1 Phase 4

### New Shopify API Endpoints

| Endpoint                             | Purpose                | Rate Limit     |
| ------------------------------------ | ---------------------- | -------------- |
| `GET /orders.json?email={email}`     | Find customer's orders | 2 calls/second |
| `GET /orders/{id}.json`              | Get order details      | 2 calls/second |
| `GET /orders/{id}/fulfillments.json` | Get tracking info      | 2 calls/second |

---

## Deliverables Checklist

From [ROADMAP.md](../../ROADMAP.md#milestone-2-order-status-agent):

- [ ] Customer verification flow (Phase 1)
- [ ] Shopify order lookup tool (Phase 1)
- [ ] Shopify fulfillment tracking — tracking numbers, URLs, carrier names (Phase 2)
- [ ] Order status response templates (Phase 1)
- [ ] Magic link authentication (Phase 1 - optional)
- [ ] WISMO analytics dashboard (Phase 3)
- [ ] Order timeline visualization (Phase 3)

---

## Risk Mitigation

| Risk                    | Mitigation                                    |
| ----------------------- | --------------------------------------------- |
| Shopify API rate limits | Implement caching, request queuing            |
| Customer data privacy   | Strict verification, audit logs               |
| Tracking data freshness | Cache with TTL, show last known status        |
| False order matches     | Multi-factor verification (order + email)     |

---

## References

- [ROADMAP.md - Milestone 2](../../ROADMAP.md#milestone-2-order-status-agent)
- [M1 Product Q&A Bot](m1-product-qa.md)
- [Shopify Admin API - Orders](https://shopify.dev/docs/api/admin-rest/2024-01/resources/order)
- [Deferred Features — Shipping Integrations](deferred-features.md)
- [LangChain Tools Documentation](https://python.langchain.com/docs/modules/tools/)

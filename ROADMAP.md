# 🛒 E-commerce AI Support Agent — Project Roadmap

> **Project Codename:** `ecom-agent` (rename later)  
> **Goal:** Build an AI agent for Shopify stores that handles customer support, order inquiries, sales recommendations, cart recovery, and actions — all autonomously.  
> **Real-World Models:** Gorgias, Siena AI, Intercom Fin  
> **Tech Stack:** LangChain + LangGraph + Python + Next.js + Shopify API

---

## Table of Contents

1. [Project Vision](#project-vision)
2. [Market Validation](#market-validation)
3. [Product Evolution](#product-evolution)
4. [Integration Architecture](#integration-architecture)
5. [Milestone 1: Product Q&A Bot (MVP)](#milestone-1-product-qa-bot-mvp)
6. [Milestone 2: Order Status Agent](#milestone-2-order-status-agent)
7. [Milestone 3: Sales & Recommendation Agent](#milestone-3-sales--recommendation-agent)
8. [Milestone 4: Cart Recovery Agent](#milestone-4-cart-recovery-agent)
9. [Milestone 5: Full Action Agent](#milestone-5-full-action-agent)
10. [Milestone 6: Omnichannel Deployment](#milestone-6-omnichannel-deployment)
11. [Milestone 7: Analytics & Self-Improvement](#milestone-7-analytics--self-improvement)
12. [Milestone 8: Developer Platform](#milestone-8-developer-platform)
13. [Tech Stack](#tech-stack)
14. [Database Schema](#database-schema)
15. [16-Week Execution Plan](#16-week-execution-plan)
16. [Competitive Landscape](#competitive-landscape)

---

## Project Vision

**One-liner:** An AI support agent built specifically for Shopify stores that answers questions, handles orders, recovers carts, and processes returns — all autonomously.

**Why E-commerce:**
- 4.6M+ Shopify stores, growing 20%+ yearly
- 70% cart abandonment rate
- Merchants already pay for apps monthly
- Measurable ROI (tickets deflected, carts recovered)
- Shopify App Store = built-in distribution

**Why LangChain + LangGraph:**
- LangChain = execution engine (tools, chains, memory)
- LangGraph = reasoning brain (state machines, decision trees, workflows)
- Industry standard, well-documented, production-ready

---

## Product Evolution

```
M1 (MVP)        M2              M3              M4              M5              M6              M7              M8
│               │               │               │               │               │               │               │
▼               ▼               ▼               ▼               ▼               ▼               ▼               ▼
┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐
│ Product │  │ Order   │  │ Sales   │  │ Cart    │  │ Action  │  │ Omni-   │  │Analytics│  │Developer│
│ Q&A Bot │─▶│ Status  │─▶│ Agent   │─▶│Recovery │─▶│ Agent   │─▶│ Channel │─▶│ & Learn │─▶│Platform │
└─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘
     │               │               │               │               │               │
     │               │               │               │               │               │
     ▼               ▼               ▼               ▼               ▼               ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              INTEGRATIONS ADDED PER MILESTONE                            │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│  M2: AfterShip, ShipStation (Shipping)                                                  │
│  M4: Klaviyo, Postscript, GA4 (Marketing)                                               │
│  M6: Zendesk, Freshdesk, Slack (Helpdesk)                                               │
│  M8: Public API, Webhooks, Custom Tools SDK (Developer)                                 │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

Each milestone:
- Is independently launchable
- Adds measurable business value
- Introduces new LangChain/LangGraph concepts
- Includes relevant third-party integrations

---

## Integration Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              SYSTEM ARCHITECTURE                                │
│                                                                                 │
│    CUSTOMER TOUCHPOINTS              CORE ENGINE              BUSINESS SYSTEMS  │
│                                                                                 │
│    ┌─────────────┐                 ┌─────────────┐          ┌─────────────────┐│
│    │ Chat Widget │────────────────▶│             │         │    SHOPIFY      ││
│    └─────────────┘                 │             │◀───────▶│                 ││
│                                    │  LANGGRAPH  │         │ • Products      ││
│    ┌─────────────┐                 │   AGENT     │         │ • Orders        ││
│    │   Email     │────────────────▶│   BRAIN     │         │ • Customers     ││
│    └─────────────┘                 │             │         │ • Carts         ││
│                                    │             │         │ • Inventory     ││
│    ┌─────────────┐                 │             │         └─────────────────┘│
│    │  WhatsApp   │────────────────▶│             │                            │
│    └─────────────┘                 │             │          ┌─────────────────┐│
│                                    │             │◀───────▶│  KNOWLEDGE BASE ││
│    ┌─────────────┐                 │             │         │                 ││
│    │    SMS      │────────────────▶│             │         │ • Policies      ││
│    └─────────────┘                 └─────────────┘         │ • FAQs          ││
│                                           │                │ • Shipping info ││
│                                           │                └─────────────────┘│
│                                           ▼                                    │
│                                    ┌─────────────┐          ┌─────────────────┐│
│                                    │  LANGCHAIN  │◀───────▶│   EXTERNAL      ││
│                                    │    TOOLS    │         │                 ││
│                                    │             │         │ • Stripe        ││
│                                    │ • API calls │         │ • Shipping APIs ││
│                                    │ • Actions   │         │ • Email (Resend)││
│                                    │ • Lookups   │         │ • Helpdesk      ││
│                                    └─────────────┘         └─────────────────┘│
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Shopify as Primary Integration

| Data Source | Usage |
|-------------|-------|
| **Products** | Q&A, recommendations, search |
| **Orders** | Status lookup, cancellation, returns |
| **Customers** | Identity verification, history |
| **Carts** | Abandonment triggers, recovery |
| **Inventory** | Stock-aware recommendations |
| **Pages** | Policies, FAQs, shipping info |

---

## Milestone 1: Product Q&A Bot (MVP)

### Goal
Answer customer questions about products, shipping, policies — the basics every store needs.

### Timeline
3-4 weeks

### Features

| Feature | Description |
|---------|-------------|
| Chat Widget | Embeddable JS snippet, customizable colors |
| Product Sync | Auto-import products from Shopify |
| Knowledge Base | Upload FAQs, policies, shipping info |
| Product Context | Knows which product page customer is viewing |
| Citation Links | Links to product pages or policy pages |
| Basic Dashboard | View conversations, common questions |

### User Journeys

**Customer:**
1. Visits store, sees chat widget
2. Types: "Do you ship to Canada?"
3. AI searches knowledge base
4. Responds with answer + source link
5. Follow-up questions maintain context

**Merchant:**
1. Signs up, connects Shopify
2. Products auto-sync
3. Uploads additional FAQs/policies
4. Gets embed code, adds to site
5. Views conversations in dashboard

### Technical Components

| Component | Purpose |
|-----------|---------|
| Ingestion Pipeline | Process docs → chunk → embed → store |
| Vector Database | Store and search embeddings |
| RAG Chain | Retrieve context → generate answer |
| Citation Parser | Extract and format source references |
| Chat API | Handle messages, maintain sessions |
| Widget (React) | Embeddable component |
| Dashboard (Next.js) | Merchant management interface |

### LangChain Concepts

| Concept | Application |
|---------|-------------|
| Document Loaders | Load Shopify products, PDFs, URLs |
| Text Splitters | Chunk product descriptions |
| Embeddings | Convert text to vectors |
| Vector Stores | Store and query embeddings |
| Retrieval Chains | Combine search with generation |
| Memory | Maintain conversation context |
| Prompt Templates | E-commerce response formatting |
| Output Parsers | Structure LLM responses |

### Shopify API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /products.json` | Sync all products |
| `GET /products/{id}.json` | Get specific product |
| `GET /pages.json` | Sync policy pages |
| `GET /shop.json` | Store info |

### Success Metrics

- Response time < 3 seconds
- Citation accuracy > 95%
- "I don't know" when appropriate
- Widget loads < 500ms

### Deliverables

- [ ] Shopify OAuth app installation flow
- [ ] Product sync pipeline (initial + incremental)
- [ ] Knowledge base upload (PDF, URL, text)
- [ ] RAG pipeline with product context
- [ ] Embeddable chat widget
- [ ] Merchant dashboard
- [ ] Shopify App Store listing

---

## Milestone 2: Order Status Agent

### Goal
Answer "Where is my order?" — the #1 support question (30-50% of all tickets).

### Timeline
2-3 weeks (builds on M1)

### New Features

| Feature | Description |
|---------|-------------|
| Order Lookup | Find orders by number, email, or name |
| Customer Verification | Secure identity check before sharing info |
| Tracking Integration | Pull real-time tracking from carriers |
| Order Timeline | Show full order journey |
| Multi-Order Support | Handle customers with multiple orders |

### Security Model

```
┌────────────────────────────────────────────────────────────┐
│                 CUSTOMER VERIFICATION                      │
│                                                            │
│  Option A: Order Number + Email Match                      │
│  Customer provides: #1234 + john@email.com                 │
│  System checks: Does order #1234 belong to john@email?     │
│  If yes → Show order details                               │
│  If no → "I couldn't find that order"                      │
│                                                            │
│  Option B: Magic Link (Higher Security)                    │
│  Customer provides email → System sends secure link        │
│  Customer clicks → Authenticated session                   │
│                                                            │
│  Option C: Logged-In Customer                              │
│  Widget inherits store authentication                      │
│  Full access to their order history                        │
└────────────────────────────────────────────────────────────┘
```

### Order Status Mapping

| Shopify Status | Customer Message |
|----------------|------------------|
| `pending` | "Your order is confirmed and being prepared" |
| `paid` | "Order received! We're packing it now" |
| `fulfilled` | "Your order has shipped!" + tracking |
| `refunded` | "This order has been refunded" |

### New Shopify Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /orders.json?email={email}` | Find customer's orders |
| `GET /orders/{id}.json` | Get order details |
| `GET /orders/{id}/fulfillments.json` | Get tracking info |

### LangChain Concepts (New)

| Concept | Application |
|---------|-------------|
| Tools | Order lookup tool, tracking tool |
| Tool Calling | LLM decides when to call Shopify |
| Structured Output | Parse order data into response |
| Conditional Logic | Different flows by order status |

### Shipping Integrations

To provide accurate tracking information across all carriers, integrate with shipping aggregators:

| Integration | Purpose | Priority | API |
|-------------|---------|----------|-----|
| **AfterShip** | Unified tracking for 1000+ carriers worldwide | P0 | REST API |
| **ShipStation** | Shipping management platform data (labels, rates) | P1 | REST API |
| **Shippo** | Multi-carrier tracking and shipping rates | P2 | REST API |
| **Route** | Package protection status and claims | P2 | REST API |

**Why these integrations matter:**
- AfterShip provides a single API to track shipments across USPS, FedEx, UPS, DHL, and 1000+ other carriers
- Merchants using ShipStation get richer data: estimated delivery dates, shipping labels created
- Enables responses like: "Your package is at the Chicago sorting facility. Expected delivery: Tomorrow by 8pm"

### Deliverables

- [ ] Customer verification flow
- [ ] Shopify order lookup tool
- [ ] Carrier tracking integration (AfterShip)
- [ ] ShipStation integration (optional)
- [ ] Order status response templates
- [ ] Magic link authentication (optional)
- [ ] WISMO analytics

---

## Milestone 3: Sales & Recommendation Agent

### Goal
Transform from support-only to sales assistant that helps customers find and buy products.

### Timeline
3 weeks (builds on M1-M2)

### New Features

| Feature | Description |
|---------|-------------|
| Product Search | Natural language product finding |
| Smart Recommendations | Based on stated preferences |
| Product Comparison | Side-by-side feature comparison |
| Size/Fit Guidance | Using size charts and reviews |
| Upsell Suggestions | Relevant add-ons and upgrades |
| Inventory Awareness | Only recommend in-stock items |
| Add to Cart | Deep link to add product to cart |

### Example Conversations

**Product Discovery:**
```
Customer: "I'm looking for a gift for my mom, she likes gardening"

Agent: "I have some great options for a gardening enthusiast!

🌱 Deluxe Garden Tool Set - $49 (bestseller)
🌻 Personalized Garden Markers - $24 
🪴 Self-Watering Planter Collection - $35

Would you like more details on any of these?"
```

**Size Guidance:**
```
Customer: "Will this jacket fit me? I'm 6'2" and usually wear large"

Agent: "Based on our size chart, I'd recommend the XL for your 
height. Our jackets run slightly slim, and customers your height 
often prefer the extra length in XL.

Want me to show you what's in stock in XL?"
```

### LangGraph Introduction

This milestone introduces LangGraph state machines:

```
┌────────────────────────────────────────────────────────────┐
│                   SALES AGENT GRAPH                        │
│                                                            │
│  ┌─────────┐     ┌──────────────┐     ┌──────────────┐    │
│  │  START  │────▶│   CLASSIFY   │────▶│    ROUTE     │    │
│  └─────────┘     │    INTENT    │     └──────┬───────┘    │
│                  └──────────────┘            │             │
│            ┌─────────────┬─────────────┬─────┴────┐       │
│            ▼             ▼             ▼          ▼       │
│     ┌──────────┐  ┌──────────┐  ┌──────────┐ ┌────────┐  │
│     │ PRODUCT  │  │  ORDER   │  │   FAQ    │ │ SMALL  │  │
│     │  SEARCH  │  │  STATUS  │  │  ANSWER  │ │  TALK  │  │
│     └────┬─────┘  └──────────┘  └──────────┘ └────────┘  │
│          ▼                                                │
│     ┌──────────┐                                          │
│     │  FILTER  │                                          │
│     │  & RANK  │                                          │
│     └────┬─────┘                                          │
│          ▼                                                │
│     ┌──────────┐                                          │
│     │ RECOMMEND│                                          │
│     └────┬─────┘                                          │
│          └──────────────────────────────────────────┐     │
│                                                     ▼     │
│                                              ┌──────────┐ │
│                                              │ RESPOND  │ │
│                                              └──────────┘ │
└────────────────────────────────────────────────────────────┘
```

### LangGraph Concepts

| Concept | Application |
|---------|-------------|
| State Definition | Conversation state schema |
| Nodes | Individual processing steps |
| Edges | Connections between nodes |
| Conditional Edges | Routing based on state |
| Graph Compilation | Building executable workflow |

### Deliverables

- [ ] Natural language product search
- [ ] Recommendation engine
- [ ] Product comparison generation
- [ ] Size/fit guidance system
- [ ] Inventory-aware responses
- [ ] Add-to-cart deep links
- [ ] Sales analytics dashboard

---

## Milestone 4: Cart Recovery Agent

### Goal
Proactively recover abandoned carts through intelligent, personalized outreach.

### Timeline
3 weeks (builds on M1-M3)

### Why This Matters
**70% of carts are abandoned.** Recovering 5-10% = significant revenue.

### New Features

| Feature | Description |
|---------|-------------|
| Abandonment Webhooks | Receive Shopify cart events |
| Smart Timing | Optimal send times per customer |
| Message Personalization | AI-crafted recovery messages |
| Objection Handling | Address likely hesitations |
| Incentive Rules | When to offer discounts |
| Multi-Touch Sequences | 1hr → 24hr → 72hr follow-ups |
| Return Visitor Detection | Greet returning visitors |

### Recovery Flow

```
┌────────────────────────────────────────────────────────────┐
│                 CART RECOVERY FLOW                         │
│                                                            │
│  TRIGGER: Shopify webhook "cart_abandoned" (1 hour idle)   │
│                                                            │
│  1. ANALYZE CART                                           │
│     • Products, value, customer history                    │
│                                                            │
│  2. DETERMINE STRATEGY                                     │
│     • First-time vs returning customer                     │
│     • High-value vs low-value cart                         │
│                                                            │
│  3. SELECT CHANNEL                                         │
│     • Email (if we have it)                                │
│     • On-site popup (if they return)                       │
│     • SMS (if opted in)                                    │
│                                                            │
│  4. CRAFT MESSAGE                                          │
│     • Personalized to cart contents                        │
│     • Address likely objection                             │
│     • Include incentive if appropriate                     │
│                                                            │
│  5. SEND & TRACK                                           │
│     • Deliver, track opens/clicks/recoveries               │
└────────────────────────────────────────────────────────────┘
```

### Recovery Sequence

| Timing | Channel | Message Type |
|--------|---------|--------------|
| 1 hour | On-site popup | Gentle reminder |
| 2 hours | Email | Helpful, answer questions |
| 24 hours | Email | Social proof, reviews |
| 48 hours | Email | Scarcity (if low stock) |
| 72 hours | Email | Final offer (discount) |

### Shopify Webhooks

| Webhook | Purpose |
|---------|---------|
| `carts/create` | New cart started |
| `carts/update` | Cart modified |
| `checkouts/create` | Checkout started |
| `orders/create` | Purchase completed (stop recovery) |

### LangGraph Concepts (New)

| Concept | Application |
|---------|-------------|
| Event-Driven Nodes | Webhook triggers execution |
| Scheduled Execution | Time-delayed follow-ups |
| State Persistence | Track sequence progress |
| External Triggers | Stop sequence on purchase |

### Marketing Integrations

Coordinate cart recovery with existing marketing tools to avoid duplicate messages and maximize effectiveness:

| Integration | Purpose | Priority | API |
|-------------|---------|----------|-----|
| **Klaviyo** | Email marketing sync — check if recovery email already sent | P0 | REST API |
| **Postscript** | SMS marketing coordination — avoid duplicate texts | P1 | REST API |
| **Attentive** | Alternative SMS platform integration | P2 | REST API |
| **Google Analytics 4** | Track recovery attribution and conversions | P1 | Measurement Protocol |

**Why these integrations matter:**
- **Klaviyo** (used by 60%+ of Shopify stores): Check if they already sent a recovery email before sending yours
- **Postscript/Attentive**: Coordinate SMS timing to avoid spamming customers
- **GA4**: Attribute recovered revenue to your AI agent with UTM tracking

**Example coordination flow:**
```
Cart abandoned → Check Klaviyo: "Email scheduled in 1 hour"
                → Skip email, only show on-site popup when customer returns
                → Result: Coordinated, not annoying
```

### Deliverables

- [ ] Shopify webhook handlers
- [ ] Recovery sequence engine
- [ ] AI message generation
- [ ] Email integration (Resend)
- [ ] Klaviyo integration (check existing flows)
- [ ] On-site popup for returning visitors
- [ ] Incentive rules engine
- [ ] Recovery analytics dashboard
- [ ] GA4 conversion tracking

---

## Milestone 5: Full Action Agent

### Goal
Handle complete support lifecycle with real actions — cancellations, returns, refunds, modifications.

### Timeline
4 weeks (builds on M1-M4)

### Why This Matters
This delivers **true automation**. 60%+ resolution rates vs 30% for Q&A-only bots.

### Actions Available

| Action | Complexity | Confirmation |
|--------|------------|--------------|
| Look up order status | Low | No |
| Send tracking link | Low | No |
| Update shipping address | Medium | Yes |
| Cancel order (pre-fulfillment) | Medium | Yes |
| Initiate return | Medium | Yes |
| Process refund | High | Yes |
| Apply discount to order | Medium | Yes |

### Action Flow with Confirmation

```
Customer: "I need to cancel my order, I ordered the wrong size"

┌────────────────────────────────────────────────────────────┐
│                   ACTION AGENT FLOW                        │
│                                                            │
│  1. UNDERSTAND REQUEST                                     │
│     → Intent: order_cancellation                           │
│     → Reason: wrong_size                                   │
│                                                            │
│  2. VERIFY CUSTOMER                                        │
│     → Customer: Sarah, Order #1234                         │
│                                                            │
│  3. CHECK FEASIBILITY                                      │
│     → Order status: "Unfulfilled" ✓                        │
│     → Cancellation window: Open ✓                          │
│                                                            │
│  4. CONFIRM ACTION                                         │
│     → "I can cancel order #1234 for you right now.         │
│        Your refund of $79 will be processed within         │
│        3-5 business days. Should I proceed?"               │
│                                                            │
│  5. CUSTOMER CONFIRMS → "Yes, please cancel it"            │
│                                                            │
│  6. EXECUTE ACTION                                         │
│     → Shopify API: Cancel order #1234                      │
│     → Shopify API: Refund payment                          │
│     → Log action in audit trail                            │
│                                                            │
│  7. CONFIRM COMPLETION                                     │
│     → "Done! I've cancelled order #1234. Would you like    │
│        help reordering in a different size?"               │
└────────────────────────────────────────────────────────────┘
```

### Permission System

```
┌────────────────────────────────────────────────────────────┐
│              MERCHANT PERMISSION SETTINGS                  │
│                                                            │
│  Action                    │ Setting                       │
│  ─────────────────────────────────────────────────────────│
│  Cancel unfulfilled orders │ ✓ Enabled (confirm)           │
│  Cancel fulfilled orders   │ ✗ Disabled                    │
│  Process refunds           │ ✓ Enabled (confirm)           │
│  Refund limit              │ Up to $100                    │
│  Initiate returns          │ ✓ Enabled (confirm)           │
│  Apply discounts           │ ✓ Enabled (max 20%)           │
└────────────────────────────────────────────────────────────┘
```

### LangGraph Action Flow

```
┌────────────────────────────────────────────────────────────────────────┐
│                         ACTION GRAPH                                   │
│                                                                        │
│  START ──▶ CLASSIFY ──▶ CHECK PERMISSION                              │
│                              │                                         │
│              ┌───────────────┼───────────────┐                        │
│              ▼               ▼               ▼                        │
│        ┌──────────┐   ┌──────────┐   ┌──────────┐                    │
│        │ ALLOWED  │   │ CONFIRM  │   │ DISABLED │                    │
│        │   AUTO   │   │ REQUIRED │   │  ACTION  │                    │
│        └────┬─────┘   └────┬─────┘   └────┬─────┘                    │
│             │              ▼              │                           │
│             │      ┌──────────────┐       │                           │
│             │      │   REQUEST    │       │                           │
│             │      │ CONFIRMATION │       │                           │
│             │      └──────┬───────┘       │                           │
│             │              ▼              │                           │
│             │      ┌──────────────┐       │                           │
│             │      │ WAIT (chkpt) │       │                           │
│             │      └──────┬───────┘       │                           │
│             │        confirmed?           │                           │
│             │         │    │              │                           │
│             │        YES   NO             │                           │
│             ▼         ▼    ▼              ▼                           │
│        ┌──────────────────────────┐  ┌─────────┐                     │
│        │      EXECUTE ACTION      │  │ EXPLAIN │                     │
│        └────────────┬─────────────┘  │ HANDOFF │                     │
│                     ▼                └────┬────┘                     │
│        ┌──────────────────────────┐       │                          │
│        │      LOG & RESPOND       │◀──────┘                          │
│        └──────────────────────────┘                                  │
└────────────────────────────────────────────────────────────────────────┘
```

### LangGraph Concepts (Advanced)

| Concept | Application |
|---------|-------------|
| Human-in-the-Loop | Confirmation before actions |
| Checkpointing | Save state while waiting |
| Tool Permissions | Check what's allowed |
| Error Recovery | Handle failed API calls |
| Subgraphs | Reusable action patterns |

### New Shopify Endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /orders/{id}/cancel.json` | Cancel order |
| `POST /orders/{id}/refund.json` | Process refund |
| `PUT /orders/{id}.json` | Update order |

### Deliverables

- [ ] Action permission system
- [ ] Confirmation flow with checkpointing
- [ ] Order cancellation tool
- [ ] Refund processing tool
- [ ] Return initiation tool
- [ ] Complete audit logging
- [ ] Escalation to human flow

---

## Milestone 6: Omnichannel Deployment

### Goal
Deploy across all touchpoints — chat, email, WhatsApp, SMS — with unified memory.

### Timeline
3-4 weeks (builds on M1-M5)

### New Channels

| Channel | Provider | Use Case |
|---------|----------|----------|
| Email Inbound | SendGrid/Resend | Support emails |
| WhatsApp | Twilio/Meta API | Quick exchanges |
| SMS | Twilio | Urgent alerts |
| Messenger | Meta API | Social support |

### Channel Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         OMNICHANNEL LAYER                               │
│                                                                         │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐│
│   │   Chat   │  │  Email   │  │ WhatsApp │  │   SMS    │  │ Messenger││
│   └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘│
│        └─────────────┴─────────────┴─────────────┴─────────────┘       │
│                                    │                                    │
│                                    ▼                                    │
│                     ┌───────────────────────────────┐                  │
│                     │      MESSAGE NORMALIZER       │                  │
│                     │  • Unified format             │                  │
│                     │  • Customer identification    │                  │
│                     │  • Context loading            │                  │
│                     └──────────────┬────────────────┘                  │
│                                    ▼                                    │
│                     ┌───────────────────────────────┐                  │
│                     │       CUSTOMER PROFILE        │                  │
│                     │  • All conversations          │                  │
│                     │  • Order history              │                  │
│                     │  • Channel preferences        │                  │
│                     └──────────────┬────────────────┘                  │
│                                    ▼                                    │
│                     ┌───────────────────────────────┐                  │
│                     │      AGENT CORE (M1-M5)       │                  │
│                     └──────────────┬────────────────┘                  │
│                                    ▼                                    │
│                     ┌───────────────────────────────┐                  │
│                     │     RESPONSE FORMATTER        │                  │
│                     │  • Channel-specific format    │                  │
│                     │  • Length constraints         │                  │
│                     └───────────────────────────────┘                  │
└─────────────────────────────────────────────────────────────────────────┘
```

### Cross-Channel Memory

Customers can switch channels seamlessly:
- Start on chat → follow up via email
- Ask on WhatsApp → check status on web
- Agent remembers full history across channels

### LangGraph Concepts (New)

| Concept | Application |
|---------|-------------|
| External Memory | PostgreSQL/Redis persistence |
| Async Execution | Non-blocking handlers |
| Memory Summarization | Compress long histories |
| Context Injection | Load profile into state |

### Helpdesk Integrations

For complex issues that need human intervention, seamlessly escalate to existing helpdesk tools with full context:

| Integration | Purpose | Priority | API |
|-------------|---------|----------|-----|
| **Slack** | Instant team notifications on escalation | P0 | Webhooks/API |
| **Zendesk** | Create tickets with full conversation context | P1 | REST API |
| **Freshdesk** | Popular SMB helpdesk integration | P2 | REST API |
| **Intercom** | Seamless handoff to human agents | P2 | REST API |
| **Gorgias** | For stores already using Gorgias | P2 | REST API |

**Why these integrations matter:**
- AI won't handle 100% of tickets — complex issues need humans
- Escalation WITH context means agents don't start from scratch
- Slack integration enables instant team response for urgent issues

**Escalation flow example:**
```
Customer: "I want to return this but I modified it"
AI: "Let me connect you with our team who handles special cases"
→ Creates Zendesk ticket with:
  • Full conversation history
  • Order details (#1234, $79, shipped Jan 15)
  • Customer's modification description
  • Sentiment analysis: "frustrated"
→ Human agent sees everything, responds within 2 hours
```

### Social Commerce Integrations (Future)

| Integration | Purpose | Priority |
|-------------|---------|----------|
| **Instagram DMs** | Handle product questions via Instagram | P3 |
| **TikTok Shop** | Support for TikTok commerce | P3 |
| **Facebook Messenger** | Social support channel | P2 |

### Deliverables

- [ ] Email inbound parsing
- [ ] WhatsApp Business integration
- [ ] SMS (Twilio) integration
- [ ] Slack escalation notifications
- [ ] Zendesk ticket creation
- [ ] Customer profile system
- [ ] Cross-channel memory
- [ ] Channel-specific formatters
- [ ] Unified inbox dashboard

---

## Milestone 7: Analytics & Self-Improvement

### Goal
Track performance, identify gaps, and help the agent improve automatically.

### Timeline
3 weeks (builds on M1-M6)

### Analytics Dashboard

```
┌────────────────────────────────────────────────────────────────────────┐
│                         KEY METRICS (This Month)                       │
│                                                                        │
│   Conversations    Resolution Rate    Avg Response    Savings          │
│      4,328            67.3%             1.2s          $12,450          │
│      ↑ 12%            ↑ 5%             ↓ 0.3s         ↑ 23%            │
└────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────┐
│                    RESOLUTION BREAKDOWN                                │
│                                                                        │
│   ████████████████████████░░░░░░░░░░  67% AI Resolved                 │
│   ██████████░░░░░░░░░░░░░░░░░░░░░░░░  23% Escalated to Human          │
│   ████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  10% Abandoned                   │
└────────────────────────────────────────────────────────────────────────┘
```

### Self-Improvement Features

**Content Gap Detection:**
- Analyze low-confidence responses
- Surface topics needing better coverage
- Auto-generate article drafts for review

### LangSmith Integration

| Feature | Purpose |
|---------|---------|
| Tracing | Track every LLM call |
| Evaluation | Score response quality |
| Datasets | Build test sets |
| A/B Testing | Compare variations |

### Deliverables

- [ ] Analytics data pipeline
- [ ] Executive dashboard
- [ ] Content gap detection
- [ ] Auto article generation
- [ ] Quality scoring system
- [ ] ROI calculator
- [ ] LangSmith integration
- [ ] Weekly email reports

---

## Milestone 8: Developer Platform

### Goal
Transform from a product into a platform — enable developers and agencies to extend, customize, and build on top of the agent.

### Timeline
4-5 weeks (builds on M1-M7)

### Why This Matters
- Developers build integrations you can't build alone
- Agencies can white-label and customize for their clients
- Community creates plugins = faster feature growth
- Platform creates a stronger moat than features alone
- Enables ecosystem similar to Shopify's app store model

### Platform Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           DEVELOPER PLATFORM                                     │
│                                                                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                 │
│  │   PUBLIC API    │  │    WEBHOOKS     │  │  CUSTOM TOOLS   │                 │
│  │                 │  │                 │  │      SDK        │                 │
│  │  • REST/GraphQL │  │  • Real-time    │  │                 │                 │
│  │  • Auth (OAuth) │  │    events       │  │  • Extend AI    │                 │
│  │  • Rate limits  │  │  • Retry logic  │  │  • Add actions  │                 │
│  │  • Versioning   │  │  • Signatures   │  │  • Custom APIs  │                 │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘                 │
│           │                    │                    │                          │
│           └────────────────────┼────────────────────┘                          │
│                                ▼                                                │
│                    ┌─────────────────────────┐                                 │
│                    │    DEVELOPER PORTAL     │                                 │
│                    │                         │                                 │
│                    │  • API documentation    │                                 │
│                    │  • SDK downloads        │                                 │
│                    │  • API key management   │                                 │
│                    │  • Usage analytics      │                                 │
│                    │  • Sandbox environment  │                                 │
│                    └─────────────────────────┘                                 │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                    APP MARKETPLACE (Future)                              │   │
│  │                                                                          │   │
│  │   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐               │   │
│  │   │ Loyalty  │  │ Reviews  │  │Subscript-│  │  Custom  │               │   │
│  │   │ Plugins  │  │ Plugins  │  │   ions   │  │  Tools   │               │   │
│  │   └──────────┘  └──────────┘  └──────────┘  └──────────┘               │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 1. Public REST API

Allow programmatic access to all data and actions:

| Resource | Methods | Use Case |
|----------|---------|----------|
| `/conversations` | GET, LIST | Pull chat history into CRM |
| `/messages` | GET, LIST, POST | Send messages programmatically |
| `/customers` | GET, LIST, UPDATE | Sync with external customer DB |
| `/products` | GET, LIST, SYNC | Trigger product re-sync |
| `/knowledge` | CRUD | Manage FAQs programmatically |
| `/orders` | GET, LIST | Access order data from conversations |
| `/analytics` | GET | Pull metrics into BI tools |
| `/agents` | GET, UPDATE | Configure AI agent settings |

**Authentication:** OAuth 2.0 with scopes for granular permissions.

**Example API calls:**
```bash
# Get all conversations from last 7 days
GET /api/v1/conversations?since=2026-01-16&status=resolved

# Sync knowledge base from external CMS
POST /api/v1/knowledge
{
  "title": "Return Policy Update",
  "content": "...",
  "source": "cms_sync"
}

# Get analytics for ROI reporting
GET /api/v1/analytics?metrics=resolution_rate,savings&period=monthly
```

### 2. Webhooks

Real-time event notifications to external systems:

| Event | Trigger | Payload |
|-------|---------|---------|
| `conversation.created` | New chat started | Customer info, initial message, channel |
| `conversation.resolved` | AI or human resolved | Resolution method, duration, satisfaction |
| `conversation.escalated` | Handed to human | Reason, conversation history, sentiment |
| `message.received` | Customer sends message | Message content, intent detected |
| `message.sent` | AI/agent responds | Response, sources used, confidence |
| `action.requested` | AI wants to take action | Action type, parameters, requires_confirm |
| `action.completed` | Action executed | Result, order affected, audit trail |
| `cart.abandoned` | Cart recovery triggered | Cart contents, customer, value |
| `cart.recovered` | Customer completed purchase | Revenue recovered, attribution |
| `feedback.received` | Customer rates interaction | Rating, comments, conversation_id |

**Webhook security:** HMAC signatures for payload verification.

**Example webhook payload:**
```json
{
  "event": "conversation.escalated",
  "timestamp": "2026-01-23T10:30:00Z",
  "store_id": "shop_123",
  "data": {
    "conversation_id": "conv_abc",
    "customer_email": "john@example.com",
    "escalation_reason": "refund_over_limit",
    "ai_summary": "Customer wants $500 refund, exceeds $100 auto-approval",
    "sentiment": "frustrated",
    "priority": "high"
  }
}
```

### 3. Custom Tools SDK

Allow developers to extend AI capabilities with custom actions:

```
┌────────────────────────────────────────────────────────────────────────┐
│                         CUSTOM TOOL FLOW                                │
│                                                                         │
│   Customer: "Can I check my loyalty points?"                           │
│                      │                                                  │
│                      ▼                                                  │
│   ┌─────────────────────────────────────────┐                          │
│   │           AI AGENT BRAIN                │                          │
│   │                                         │                          │
│   │   "I need to check loyalty points"      │                          │
│   │   Available tools:                      │                          │
│   │   ✓ get_order_status (built-in)        │                          │
│   │   ✓ search_products (built-in)         │                          │
│   │   ✓ check_loyalty_points (CUSTOM) ◄────┼─── Merchant installed    │
│   └────────────────┬────────────────────────┘                          │
│                    │                                                    │
│                    ▼                                                    │
│   ┌─────────────────────────────────────────┐                          │
│   │    CUSTOM TOOL: check_loyalty_points    │                          │
│   │    Calls: GET merchant.com/api/loyalty  │                          │
│   │    Returns: { "points": 2500 }          │                          │
│   └────────────────┬────────────────────────┘                          │
│                    │                                                    │
│                    ▼                                                    │
│   AI: "You have 2,500 loyalty points! That's enough for $25 off."     │
└────────────────────────────────────────────────────────────────────────┘
```

**Tool Definition Format (YAML):**
```yaml
name: check_loyalty_points
description: "Check customer's loyalty points balance"
version: "1.0"

triggers:
  - "loyalty points"
  - "rewards balance"
  - "how many points"

parameters:
  - name: customer_email
    type: string
    required: true
    source: conversation  # Auto-filled from context

endpoint:
  url: "https://{{store.loyalty_api_url}}/points"
  method: GET
  headers:
    Authorization: "Bearer {{store.loyalty_api_key}}"
  query:
    email: "{{customer_email}}"

response_mapping:
  points: "data.balance"
  tier: "data.membership_tier"

response_template: |
  You have {{points}} loyalty points and you're a {{tier}} member!
```

**Example Custom Tools:**

| Tool | Use Case | Who Needs It |
|------|----------|--------------|
| `check_loyalty_points` | Query loyalty program | Stores with rewards |
| `book_appointment` | Schedule in-store visit | Retail with locations |
| `check_warranty` | Look up warranty status | Electronics stores |
| `get_size_recommendation` | Query fit predictor | Fashion/apparel |
| `check_prescription_status` | Verify Rx status | Eyewear, pharmacy |
| `calculate_custom_price` | B2B custom pricing | Wholesale stores |
| `check_inventory_location` | Which store has stock | Multi-location retail |

### 4. Embeddable SDK

JavaScript SDK for custom widget implementations:

```javascript
import { RevaChat } from '@reva/sdk';

const chat = new RevaChat({
  storeId: 'your-store-id',
  apiKey: 'your-api-key',
  
  // Theming
  theme: {
    primaryColor: '#FF6B6B',
    fontFamily: 'Inter',
    borderRadius: '12px',
    position: 'bottom-right',
  },
  
  // Custom greeting
  greeting: 'Hey! How can I help you today?',
  
  // Event callbacks
  onMessage: (message) => {
    analytics.track('chat_message', message);
  },
  onEscalation: (conversation) => {
    notifyTeam(conversation);
  },
  
  // Context injection
  context: {
    currentProduct: getProductFromPage(),
    cartContents: getCart(),
    customerSegment: 'vip',
  },
});

// Programmatic control
chat.open();
chat.sendMessage('I need help with order #1234');
chat.setCustomer({ email: 'john@example.com' });
```

**White-label options:**
- Remove "Powered by" branding
- Custom domain for widget assets
- Full CSS override capability

### 5. App Marketplace (Future - M9+)

Directory of pre-built integrations:

| Category | Example Apps |
|----------|--------------|
| **Loyalty** | Smile.io, LoyaltyLion, Yotpo Loyalty |
| **Reviews** | Yotpo, Judge.me, Stamped |
| **Subscriptions** | Recharge, Bold, Skio |
| **Helpdesk** | Zendesk, Freshdesk, Intercom |
| **Marketing** | Klaviyo, Postscript, Attentive |
| **Shipping** | AfterShip, ShipStation, Route |
| **Analytics** | Google Analytics, Mixpanel, Amplitude |

**Developer monetization:**
- Free apps (for exposure)
- Paid apps (70/30 revenue share)
- Freemium (basic free, premium paid)

### LangGraph Concepts (New)

| Concept | Application |
|---------|-------------|
| Dynamic Tool Loading | Load custom tools at runtime based on store config |
| Tool Registry | Manage available tools per store |
| External Tool Execution | Securely call third-party APIs with timeout/retry |
| Tool Permission Scopes | Limit what custom tools can access |

### API Rate Limits

| Tier | Requests/min | Webhooks/day | Custom Tools |
|------|--------------|--------------|--------------|
| Free | 60 | 1,000 | 3 |
| Pro | 300 | 10,000 | 10 |
| Enterprise | 1,000+ | Unlimited | Unlimited |

### Database Schema Additions

```sql
-- API Keys
api_keys (
  id, org_id, key_hash, name, scopes_json, 
  rate_limit, last_used_at, created_at
)

-- Webhooks
webhooks (
  id, org_id, url, events_json, secret_hash,
  is_active, failure_count, created_at
)

-- Custom Tools
custom_tools (
  id, org_id, name, definition_yaml, 
  is_active, usage_count, created_at
)

-- Webhook Deliveries (for retry logic)
webhook_deliveries (
  id, webhook_id, event_type, payload_json,
  status, attempts, next_retry_at, created_at
)
```

### Deliverables

- [ ] Public REST API with OAuth 2.0
- [ ] API documentation site (Swagger/OpenAPI)
- [ ] Webhook system with retry logic
- [ ] Webhook signature verification
- [ ] Custom Tools SDK (beta)
- [ ] Tool definition validator
- [ ] JavaScript embed SDK
- [ ] Developer portal
- [ ] API key management UI
- [ ] Usage analytics dashboard
- [ ] Rate limiting infrastructure
- [ ] SDK libraries (Node.js, Python)
- [ ] Sandbox environment for testing

---

## Tech Stack

| Layer | Technology | Why |
|-------|------------|-----|
| **LLM** | Claude API | Best reasoning |
| **Agent Framework** | LangChain + LangGraph | Industry standard |
| **Vector Database** | Pinecone | Managed, scalable |
| **Primary Database** | PostgreSQL | Reliable, JSON support |
| **Cache** | Redis | Sessions, queues |
| **Backend** | Python FastAPI | Async, LangChain native |
| **Frontend** | Next.js | Dashboard |
| **Widget** | React | Embeddable |
| **Email** | Resend | Modern, simple |
| **SMS/Voice** | Twilio | Industry standard |
| **Monitoring** | LangSmith | LLM observability |
| **Hosting** | Railway/Render | Simple deployment |

---

## Database Schema

### Core Tables

```sql
-- Organizations (Shopify stores)
organizations (
  id, shopify_store_url, shopify_access_token, 
  plan, settings_json, created_at
)

-- Products (synced from Shopify)
products (
  id, org_id, shopify_product_id, title, 
  description, variants_json, tags, synced_at
)

-- Knowledge articles
knowledge_articles (
  id, org_id, type, title, content, 
  embedding_id, created_at
)

-- Conversations
conversations (
  id, org_id, session_id, customer_email, 
  channel, resolved, started_at
)

-- Messages
messages (
  id, conversation_id, role, content, 
  sources_json, created_at
)

-- Customer profiles (M6)
customers (
  id, org_id, email, phone, name, 
  shopify_customer_id, preferences_json
)

-- Action audit log (M5)
action_audit_log (
  id, org_id, conversation_id, action_type, 
  parameters_json, result, executed_at
)

-- Cart recovery (M4)
abandoned_carts (
  id, org_id, cart_token, customer_email, 
  cart_contents_json, abandoned_at, recovered_at
)
```

---

## 16-Week Execution Plan

| Week | Focus | Milestone | Key Integrations |
|------|-------|-----------|------------------|
| 1-2 | Shopify OAuth, product sync, basic RAG | M1: 40% | Shopify API |
| 3-4 | Chat widget, dashboard, deploy MVP | M1: 100% ✓ | - |
| 5-6 | Order lookup, verification, tracking | M2: 100% ✓ | AfterShip |
| 7-8 | Sales agent, recommendations | M3: 100% ✓ | - |
| 9-10 | Cart recovery, email sequences | M4: 100% ✓ | Klaviyo, Resend |
| 11-12 | Action agent (cancel, refund) | M5: 100% ✓ | - |
| 13-14 | Omnichannel, escalation | M6: 100% ✓ | Slack, Zendesk, Twilio |
| 15 | Analytics, LangSmith, self-improvement | M7: 100% ✓ | LangSmith, GA4 |
| 16 | Developer Platform (API, webhooks, SDK) | M8: 60% | - |

**After 16 weeks:** Full product with M1-M7 complete, developer platform foundation ready.

### Integration Rollout Summary

| Milestone | Integrations Added | Total Integrations |
|-----------|-------------------|-------------------|
| M1 | Shopify | 1 |
| M2 | + AfterShip, ShipStation | 3 |
| M3 | - | 3 |
| M4 | + Klaviyo, Resend, GA4 | 6 |
| M5 | - | 6 |
| M6 | + Slack, Zendesk, Twilio, WhatsApp | 10 |
| M7 | + LangSmith | 11 |
| M8 | + Public API, Webhooks, Custom Tools | Platform |

---

## Competitive Landscape

### Direct Competitors

| Competitor | Focus | Pricing | Your Advantage |
|------------|-------|---------|----------------|
| **Gorgias** | Full helpdesk for e-commerce | $50-300+/mo | AI-first, developer platform, cheaper |
| **Siena AI** | Enterprise AI support | Custom (enterprise) | Self-serve, open ecosystem, faster setup |
| **Tidio** | Generic chatbot | $29+/mo | E-commerce specialized, deeper Shopify |
| **Richpanel** | Self-service portal | Custom | Conversational AI, cart recovery |
| **Intercom Fin** | AI agent (general) | $0.99/resolution | Shopify-native, predictable pricing |

### Feature Comparison

| Feature | Your Product | Gorgias | Siena | Tidio | Richpanel |
|---------|-------------|---------|-------|-------|-----------|
| AI-First Architecture | ✓ | Partial | ✓ | Partial | Partial |
| Shopify Deep Integration | ✓ | ✓ | ✓ | Partial | ✓ |
| Cart Recovery | ✓ | ✗ | ✗ | ✗ | ✗ |
| Order Actions (cancel/refund) | ✓ | ✓ | ✓ | ✗ | ✓ |
| Developer Platform/API | ✓ | Partial | ✗ | ✗ | Partial |
| Custom Tools SDK | ✓ | ✗ | ✗ | ✗ | ✗ |
| Open Source Option | ✓ | ✗ | ✗ | ✗ | ✗ |
| White-Label | ✓ | ✗ | ✓ | ✓ | ✓ |

### Integration Comparison

| Integration | Your Product | Gorgias | Siena | Tidio |
|-------------|-------------|---------|-------|-------|
| Shopify | ✓ Native | ✓ Native | ✓ | ✓ |
| Klaviyo | ✓ M4 | ✓ | ✓ | ✗ |
| AfterShip | ✓ M2 | ✓ | ✗ | ✗ |
| Zendesk | ✓ M6 | ✗ | ✓ | ✗ |
| Slack | ✓ M6 | ✓ | ✗ | ✗ |
| WhatsApp | ✓ M6 | ✓ | ✓ | ✓ |
| Custom APIs | ✓ M8 | ✗ | ✗ | ✗ |

### Open Source Alternatives

| Project | Stars | Focus | Gap vs Your Product |
|---------|-------|-------|---------------------|
| **Chatwoot** | 27k | Generic helpdesk | No e-commerce AI, no Shopify depth |
| **Botpress** | 14k | Chatbot builder | Not support-focused, no actions |
| **Typebot** | 9k | Form/flow builder | No helpdesk, no AI agent |

**Your unique position:** First open-source, e-commerce-specific AI support agent with developer platform.

### Positioning

> "The open-source AI support agent built specifically for Shopify. Setup in 10 minutes. Handles 60% of tickets automatically. Extend with custom tools."

**For different audiences:**
- **SMB Merchants:** "Gorgias-level AI at 1/10th the cost"
- **Agencies:** "White-label AI support for all your Shopify clients"
- **Developers:** "Build on top of a modern LangChain/LangGraph stack"
- **Enterprise:** "Self-host, own your data, extend with custom tools"

---

## Next Steps

1. [ ] Finalize project name
2. [ ] Set up repository structure
3. [ ] Create Shopify Partner account
4. [ ] Build M1 MVP
5. [ ] Launch on Shopify App Store

---

---

## Integration Summary

### All Integrations by Category

| Category | Integration | Milestone | Priority | Purpose |
|----------|-------------|-----------|----------|---------|
| **E-commerce** | Shopify | M1 | P0 | Core platform |
| **Shipping** | AfterShip | M2 | P0 | Unified tracking |
| **Shipping** | ShipStation | M2 | P1 | Shipping management |
| **Shipping** | Shippo | M2 | P2 | Multi-carrier |
| **Shipping** | Route | M2 | P2 | Package protection |
| **Marketing** | Klaviyo | M4 | P0 | Email coordination |
| **Marketing** | Postscript | M4 | P1 | SMS coordination |
| **Marketing** | Attentive | M4 | P2 | SMS alternative |
| **Analytics** | Google Analytics 4 | M4 | P1 | Conversion tracking |
| **Communication** | Resend | M4 | P0 | Transactional email |
| **Communication** | Twilio | M6 | P0 | SMS/WhatsApp |
| **Communication** | WhatsApp Business | M6 | P1 | Messaging channel |
| **Helpdesk** | Slack | M6 | P0 | Team notifications |
| **Helpdesk** | Zendesk | M6 | P1 | Ticket escalation |
| **Helpdesk** | Freshdesk | M6 | P2 | SMB helpdesk |
| **Helpdesk** | Intercom | M6 | P2 | Human handoff |
| **Observability** | LangSmith | M7 | P0 | LLM monitoring |
| **Social** | Instagram DMs | Future | P3 | Social commerce |
| **Social** | Facebook Messenger | M6 | P2 | Social support |

### Integration Priority Legend

- **P0:** Must have for milestone launch
- **P1:** Important, include if time permits
- **P2:** Nice to have, can defer
- **P3:** Future consideration

---

*Last updated: January 2026*
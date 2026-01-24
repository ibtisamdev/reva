# Phase 3: Dashboard Features

> **Parent:** [M1 Product Q&A Bot](../m1-product-qa.md)  
> **Duration:** 1 week  
> **Status:** Not Started  
> **Depends on:** Phase 1 (RAG Pipeline)

---

## Goal

Build the merchant-facing dashboard for managing knowledge base content, viewing conversations, and configuring the widget.

---

## Current State

The dashboard exists at `apps/web/` with:

- Next.js 15 with App Router
- Better Auth authentication (email/password + Google OAuth)
- Basic layout and navigation
- Protected routes with session management

**Existing pages:**

- `/` - Landing page
- `/sign-in`, `/sign-up` - Auth pages
- `/dashboard` - Basic dashboard shell

---

## Tasks

### 3.1 Knowledge Base Upload UI

**Location:** `apps/web/src/app/dashboard/knowledge/`

- [ ] Create knowledge base list page `/dashboard/knowledge`
- [ ] Show existing knowledge articles
- [ ] Implement upload form for new content:
  - [ ] Text input (paste content)
  - [ ] PDF file upload
  - [ ] URL input (fetch from web)
- [ ] Show processing status (pending, processing, ready)
- [ ] Support edit/delete of existing articles

**UI Layout:**

```
┌─────────────────────────────────────────────────────────┐
│ Knowledge Base                        [+ Add Content]   │
├─────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────┐ │
│ │ Shipping Policy                    Ready    [Edit]  │ │
│ │ Uploaded Jan 20, 2026 • 3 chunks                    │ │
│ └─────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ Return Policy                      Ready    [Edit]  │ │
│ │ Uploaded Jan 18, 2026 • 5 chunks                    │ │
│ └─────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ FAQ Document                       Processing...    │ │
│ │ Uploaded just now                                   │ │
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

**API Endpoints:**

- `GET /api/v1/knowledge` - List knowledge articles
- `POST /api/v1/knowledge` - Upload new content
- `PUT /api/v1/knowledge/{id}` - Update article
- `DELETE /api/v1/knowledge/{id}` - Delete article

### 3.2 Conversations List

**Location:** `apps/web/src/app/dashboard/conversations/`

- [ ] Create conversations list page `/dashboard/conversations`
- [ ] Show all conversations for the store
- [ ] Display: customer name/email, last message, timestamp, status
- [ ] Support filtering by status (active, resolved)
- [ ] Support search by customer or message content
- [ ] Pagination for large lists

**UI Layout:**

```
┌─────────────────────────────────────────────────────────┐
│ Conversations                   [Search...] [Filter ▼] │
├─────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────┐ │
│ │ John D.                               5 mins ago    │ │
│ │ "Do you have this in size XL?"                      │ │
│ │ 🟢 Active • 4 messages                              │ │
│ └─────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ sarah@email.com                       2 hours ago   │ │
│ │ "Thanks for the help!"                              │ │
│ │ ✓ Resolved • 8 messages                             │ │
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

**API Endpoints:**

- `GET /api/v1/conversations` - List conversations
- `GET /api/v1/conversations?status=active` - Filter by status

### 3.3 Conversation Detail View

**Location:** `apps/web/src/app/dashboard/conversations/[id]/`

- [ ] Create conversation detail page `/dashboard/conversations/[id]`
- [ ] Display full message history
- [ ] Show customer info sidebar
- [ ] Show context (page URL, product viewed)
- [ ] Display citations used in responses
- [ ] Mark conversation as resolved

**UI Layout:**

```
┌─────────────────────────────────────────────────────────┐
│ ← Back                                    [Resolve ✓]  │
├───────────────────────────────────┬─────────────────────┤
│                                   │ Customer Info       │
│ Customer: Do you ship to Canada? │ ─────────────────── │
│ 10:30 AM                         │ Email: john@...     │
│                                   │ First seen: Jan 20 │
│ Agent: Yes, we ship to Canada!   │ Messages: 4         │
│ Standard shipping takes 5-7      │                     │
│ business days. [Shipping Policy] │ Context             │
│ 10:31 AM                         │ ─────────────────── │
│                                   │ Page: Winter Jacket │
│ Customer: Great, thanks!         │ URL: /products/...  │
│ 10:32 AM                         │                     │
└───────────────────────────────────┴─────────────────────┘
```

**API Endpoints:**

- `GET /api/v1/conversations/{id}` - Get conversation with messages
- `PUT /api/v1/conversations/{id}` - Update status

### 3.4 Widget Customization

**Location:** `apps/web/src/app/dashboard/settings/widget/`

- [ ] Create widget settings page `/dashboard/settings/widget`
- [ ] Color customization (primary color)
- [ ] Welcome message configuration
- [ ] Widget position (bottom-right, bottom-left)
- [ ] Live preview of widget

**UI Layout:**

```
┌─────────────────────────────────────────────────────────┐
│ Widget Settings                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ Primary Color          Welcome Message                  │
│ [#007bff    ] [🎨]    [Hi! How can I help you today?]  │
│                                                         │
│ Position               Widget Icon                      │
│ ○ Bottom Right         ○ Chat bubble                    │
│ ○ Bottom Left          ○ Question mark                  │
│                                                         │
│ ─────────────────────────────────────────────────────── │
│                                                         │
│ Preview:                                                │
│ ┌─────────────────┐                                     │
│ │ [Widget Preview]│                                     │
│ └─────────────────┘                                     │
│                                                         │
│                                         [Save Changes]  │
└─────────────────────────────────────────────────────────┘
```

**API Endpoints:**

- `GET /api/v1/stores/{id}/settings` - Get widget settings
- `PUT /api/v1/stores/{id}/settings` - Update settings

### 3.5 Embed Code Generator

**Location:** `apps/web/src/app/dashboard/settings/widget/`

- [ ] Generate embed code snippet
- [ ] Include store ID and API URL
- [ ] Copy-to-clipboard button
- [ ] Installation instructions

**Embed code output:**

```html
<!-- Reva Chat Widget -->
<script>
  window.RevaConfig = {
    storeId: 'store_abc123',
    apiUrl: 'https://api.reva.ai',
  };
</script>
<script src="https://widget.reva.ai/widget.js" async></script>
```

### 3.6 Navigation Updates

**Location:** `apps/web/src/components/`

- [ ] Add navigation links to new pages
- [ ] Update sidebar/header navigation
- [ ] Add active state styling
- [ ] Breadcrumb navigation

**Navigation structure:**

```
Dashboard
├── Overview (home)
├── Conversations
├── Knowledge Base
├── Products (Phase 4)
└── Settings
    └── Widget
```

---

## Files to Create/Modify

| File                                            | Action | Purpose                  |
| ----------------------------------------------- | ------ | ------------------------ |
| `app/dashboard/knowledge/page.tsx`              | Create | Knowledge list           |
| `app/dashboard/knowledge/new/page.tsx`          | Create | Add knowledge            |
| `app/dashboard/knowledge/[id]/page.tsx`         | Create | Edit knowledge           |
| `app/dashboard/conversations/page.tsx`          | Create | Conversations list       |
| `app/dashboard/conversations/[id]/page.tsx`     | Create | Conversation detail      |
| `app/dashboard/settings/widget/page.tsx`        | Create | Widget settings          |
| `components/knowledge/KnowledgeList.tsx`        | Create | Knowledge list component |
| `components/knowledge/UploadForm.tsx`           | Create | Upload form              |
| `components/conversations/ConversationList.tsx` | Create | Conversation list        |
| `components/conversations/MessageThread.tsx`    | Create | Message display          |
| `components/widget/EmbedCode.tsx`               | Create | Embed code generator     |
| `lib/api.ts`                                    | Create | API client for dashboard |

---

## API Endpoints to Implement (Backend)

| Endpoint                       | Method | Purpose                 |
| ------------------------------ | ------ | ----------------------- |
| `/api/v1/knowledge`            | GET    | List knowledge articles |
| `/api/v1/knowledge`            | POST   | Upload new content      |
| `/api/v1/knowledge/{id}`       | GET    | Get single article      |
| `/api/v1/knowledge/{id}`       | PUT    | Update article          |
| `/api/v1/knowledge/{id}`       | DELETE | Delete article          |
| `/api/v1/conversations`        | GET    | List conversations      |
| `/api/v1/conversations/{id}`   | GET    | Get conversation        |
| `/api/v1/conversations/{id}`   | PUT    | Update conversation     |
| `/api/v1/stores/{id}/settings` | GET    | Get store settings      |
| `/api/v1/stores/{id}/settings` | PUT    | Update settings         |

---

## Testing

- [ ] Test: Can upload text content
- [ ] Test: Can upload PDF file
- [ ] Test: Knowledge list displays correctly
- [ ] Test: Conversations list loads
- [ ] Test: Conversation detail shows all messages
- [ ] Test: Widget settings save correctly
- [ ] Test: Embed code generates correctly

---

## Acceptance Criteria

1. Merchants can upload knowledge base content (text, PDF, URL)
2. Knowledge articles are listed with status
3. Conversations are listed with search/filter
4. Individual conversations can be viewed with full history
5. Widget appearance can be customized
6. Embed code can be copied for installation

---

## UI Components to Use

Leverage existing Radix UI components from the project:

- Dialog for modals
- DropdownMenu for filters
- Input, Textarea for forms
- Button, Badge for actions
- Table for lists (or custom cards)

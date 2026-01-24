# Phase 2: Widget API Integration

> **Parent:** [M1 Product Q&A Bot](../m1-product-qa.md)  
> **Duration:** 0.5 weeks  
> **Status:** Not Started  
> **Depends on:** Phase 1 (RAG Pipeline)

---

## Goal

Connect the existing chat widget UI to the backend API for an end-to-end working demo.

---

## Current State

The widget already exists at `apps/widget/` with:

- Preact-based UI components
- `ChatWindow.tsx` with message display
- `ToggleButton.tsx` for open/close
- Mock response using `setTimeout` (needs replacement)

**TODO in code:** `apps/widget/src/components/ChatWindow.tsx:44`

```typescript
// TODO: Replace with actual API call
```

---

## Tasks

### 2.1 Connect Widget to Chat API

**Location:** `apps/widget/src/`

- [ ] Create API client for chat endpoints
- [ ] Replace mock `setTimeout` with real API call
- [ ] Handle API errors gracefully
- [ ] Show loading state while waiting for response

**API client:**

```typescript
// apps/widget/src/lib/api.ts
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export async function sendMessage(
  conversationId: string | null,
  message: string,
  context?: PageContext
): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE}/api/v1/chat/messages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      conversation_id: conversationId,
      message,
      context,
    }),
  });
  return response.json();
}
```

### 2.2 Page Context Detection

**Location:** `apps/widget/src/lib/context.ts`

- [ ] Detect current page URL
- [ ] Extract product ID from URL if on product page
- [ ] Send context with each message
- [ ] Update context on page navigation (SPA support)

**Context structure:**

```typescript
interface PageContext {
  page_url: string;
  page_title: string;
  product_id?: string;
  product_handle?: string;
}

function getPageContext(): PageContext {
  const url = window.location.href;
  const productMatch = url.match(/\/products\/([^/?]+)/);

  return {
    page_url: url,
    page_title: document.title,
    product_id: productMatch?.[1],
  };
}
```

### 2.3 Session Management

**Location:** `apps/widget/src/lib/session.ts`

- [ ] Store conversation ID in localStorage
- [ ] Persist conversation across page navigations
- [ ] Handle session expiry/new conversation
- [ ] Support "New conversation" button

```typescript
const CONVERSATION_KEY = 'reva_conversation_id';

export function getConversationId(): string | null {
  return localStorage.getItem(CONVERSATION_KEY);
}

export function setConversationId(id: string): void {
  localStorage.setItem(CONVERSATION_KEY, id);
}

export function clearConversation(): void {
  localStorage.removeItem(CONVERSATION_KEY);
}
```

### 2.4 Error Handling

- [ ] Show user-friendly error messages
- [ ] Retry failed requests (with limit)
- [ ] Fallback message if API unavailable
- [ ] Log errors for debugging

**Error states:**

```typescript
type ErrorType =
  | 'network_error' // API unreachable
  | 'rate_limited' // Too many requests
  | 'server_error' // 500 errors
  | 'invalid_response'; // Malformed response
```

### 2.5 Display Citations

**Location:** `apps/widget/src/components/ChatMessage.tsx`

- [ ] Parse `sources` array from API response
- [ ] Display citation links below message
- [ ] Style citations appropriately
- [ ] Handle click to open source page

**UI design:**

```
┌─────────────────────────────────────┐
│ We ship to Canada! Standard         │
│ shipping takes 5-7 business days.   │
│                                     │
│ Sources:                            │
│ • Shipping Policy                   │
│ • International Orders FAQ          │
└─────────────────────────────────────┘
```

### 2.6 Widget Configuration

**Location:** `apps/widget/src/lib/config.ts`

- [ ] Accept configuration via embed script
- [ ] Support store ID (required)
- [ ] Support API URL override
- [ ] Support theme customization (basic)

**Embed script usage:**

```html
<script>
  window.RevaConfig = {
    storeId: 'store_123',
    apiUrl: 'https://api.reva.ai',
    theme: {
      primaryColor: '#007bff',
    },
  };
</script>
<script src="https://widget.reva.ai/widget.js"></script>
```

---

## Files to Create/Modify

| File                             | Action        | Purpose                  |
| -------------------------------- | ------------- | ------------------------ |
| `src/lib/api.ts`                 | Create        | API client               |
| `src/lib/context.ts`             | Create        | Page context detection   |
| `src/lib/session.ts`             | Create        | Conversation persistence |
| `src/lib/config.ts`              | Create        | Widget configuration     |
| `src/components/ChatWindow.tsx`  | Modify        | Replace mock with API    |
| `src/components/ChatMessage.tsx` | Modify        | Add citation display     |
| `src/types.ts`                   | Create/Modify | TypeScript interfaces    |

---

## API Endpoints Used

| Endpoint                          | Method | Purpose                    |
| --------------------------------- | ------ | -------------------------- |
| `/api/v1/chat/messages`           | POST   | Send message, get response |
| `/api/v1/chat/conversations/{id}` | GET    | Load conversation history  |

---

## Testing

- [ ] Manual test: Send message, receive response
- [ ] Test: Conversation persists across page refresh
- [ ] Test: Page context is sent correctly
- [ ] Test: Error handling when API unavailable
- [ ] Test: Citations display correctly

---

## Acceptance Criteria

1. Widget sends messages to real API (not mock)
2. AI responses display in chat
3. Conversation persists across page navigation
4. Current page context is sent with each message
5. Citations are displayed and clickable
6. Errors are handled gracefully

---

## Optional Enhancements (Future)

- [ ] Streaming responses (SSE or WebSocket)
- [ ] Typing indicator during response generation
- [ ] Message reactions (thumbs up/down)
- [ ] Sound notification for new messages

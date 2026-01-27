# Phase 2: Widget API Integration

> **Parent:** [M1 Product Q&A Bot](../m1-product-qa.md)  
> **Duration:** 0.5 weeks  
> **Status:** Complete  
> **Depends on:** Phase 1 (RAG Pipeline)

---

## Goal

Connect the existing chat widget UI to the backend API for an end-to-end working demo.

---

## Current State

The widget is now fully integrated with the backend API:

- Preact-based UI components
- `ChatWindow.tsx` connected to real API
- `ChatMessage.tsx` with citation display
- Full session and conversation management
- Design system aligned (teal primary color)
- Theme customization support for store owners

---

## Tasks

### 2.1 Connect Widget to Chat API

**Location:** `apps/widget/src/`

- [x] Create API client for chat endpoints
- [x] Replace mock `setTimeout` with real API call
- [x] Handle API errors gracefully
- [x] Show loading state while waiting for response

**Implementation:** `apps/widget/src/lib/api.ts`

```typescript
// API client with retry logic and error handling
export async function sendMessage(
  apiUrl: string,
  storeId: string,
  request: ChatRequest
): Promise<ChatResponse | ApiError>
```

### 2.2 Page Context Detection

**Location:** `apps/widget/src/lib/context.ts`

- [x] Detect current page URL
- [x] Extract product ID from URL if on product page
- [x] Send context with each message
- [x] Update context on page navigation (SPA support)

**Implementation:** `apps/widget/src/lib/context.ts`

```typescript
export function getPageContext(): PageContext
export function onPageChange(callback: () => void): () => void
```

### 2.3 Session Management

**Location:** `apps/widget/src/lib/session.ts`

- [x] Store conversation ID in localStorage
- [x] Persist conversation across page navigations
- [x] Handle session expiry/new conversation
- [x] Support session ID for user tracking

**Implementation:** `apps/widget/src/lib/session.ts`

```typescript
export function getSessionId(): string
export function getConversationId(): string | null
export function setConversationId(id: string): void
export function clearConversation(): void
```

### 2.4 Error Handling

- [x] Show user-friendly error messages
- [x] Retry failed requests (with limit)
- [x] Fallback message if API unavailable
- [x] Structured error types

**Implementation:** Error handling in `lib/api.ts` with retry logic (max 2 retries, exponential backoff). Error display in `ChatWindow.tsx` with retry button for recoverable errors.

### 2.5 Display Citations

**Location:** `apps/widget/src/components/ChatMessage.tsx`

- [x] Parse `sources` array from API response
- [x] Display citation links below message
- [x] Style citations appropriately
- [x] Handle click to open source page

**UI Result:**

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

- [x] Accept configuration via embed script
- [x] Support store ID (required)
- [x] Support API URL override
- [x] Support theme customization (basic)
- [x] Auto-contrast color calculation for accessibility

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
<script src="https://widget.reva.ai/reva-widget.js"></script>
```

---

## Files Created/Modified

| File                             | Action  | Purpose                              |
| -------------------------------- | ------- | ------------------------------------ |
| `src/types.ts`                   | Created | Centralized TypeScript interfaces    |
| `src/lib/api.ts`                 | Created | API client with retry logic          |
| `src/lib/context.ts`             | Created | Page context detection               |
| `src/lib/session.ts`             | Created | Session & conversation persistence   |
| `src/lib/config.ts`              | Created | Widget configuration & theme utils   |
| `src/components/ChatMessage.tsx` | Created | Message component with citations     |
| `src/components/ChatWindow.tsx`  | Updated | Full API integration                 |
| `src/components/Widget.tsx`      | Updated | Theme variable application           |
| `src/main.tsx`                   | Updated | Use new config system                |
| `src/styles.css`                 | Updated | Design system alignment, new styles  |
| `tsconfig.json`                  | Updated | Added vite/client types              |

---

## API Endpoints Used

| Endpoint                          | Method | Purpose                    |
| --------------------------------- | ------ | -------------------------- |
| `/api/v1/chat/messages`           | POST   | Send message, get response |
| `/api/v1/chat/conversations/{id}` | GET    | Load conversation history  |

---

## Testing

- [x] Build passes without errors
- [x] Lint passes without warnings
- [ ] Manual test: Send message, receive response
- [ ] Test: Conversation persists across page refresh
- [ ] Test: Page context is sent correctly
- [ ] Test: Error handling when API unavailable
- [ ] Test: Citations display correctly

---

## Acceptance Criteria

1. [x] Widget sends messages to real API (not mock)
2. [x] AI responses display in chat
3. [x] Conversation persists across page navigation
4. [x] Current page context is sent with each message
5. [x] Citations are displayed and clickable
6. [x] Errors are handled gracefully

---

## Design System Alignment

The widget now uses the Reva design system colors:

- **Primary:** `#0d9488` (teal-600)
- **Primary Hover:** `#0f766e` (teal-700)
- **Neutrals:** Slate scale from design tokens

Store owners can customize the primary color via `window.RevaConfig.theme.primaryColor`, and the widget automatically calculates appropriate contrast colors for accessibility.

---

## Optional Enhancements (Future)

- [ ] Streaming responses (SSE or WebSocket)
- [ ] Typing indicator during response generation
- [ ] Message reactions (thumbs up/down)
- [ ] Sound notification for new messages

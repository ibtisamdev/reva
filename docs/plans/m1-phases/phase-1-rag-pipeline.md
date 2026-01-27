# Phase 1: Core AI/RAG Pipeline

> **Parent:** [M1 Product Q&A Bot](../m1-product-qa.md)  
> **Duration:** 1.5 weeks  
> **Status:** Completed

---

## Goal

Build the knowledge ingestion pipeline and RAG (Retrieval-Augmented Generation) system that powers AI responses.

---

## Tasks

### 1.1 Knowledge Ingestion Service

**Location:** `apps/api/app/services/knowledge_service.py`

- [x] Create document ingestion endpoint `POST /api/v1/knowledge`
- [x] Implement text chunking (512 tokens, 50 token overlap)
- [x] Support multiple input types:
  - [x] Plain text
  - [ ] PDF files (deferred to Phase 2)
  - [ ] URLs (deferred to Phase 2)
- [x] Generate embeddings using OpenAI `text-embedding-3-small`
- [x] Store chunks + embeddings in `knowledge_chunks` table (pgvector)
- [x] Handle large documents async via Celery task

**Database Schema:**

```sql
-- Added via migration 73487033ba80
ALTER TABLE knowledge_chunks ADD COLUMN token_count INTEGER;
```

### 1.2 RAG Retrieval Service

**Location:** `apps/api/app/services/retrieval_service.py`

- [x] Implement vector similarity search using pgvector
- [x] Query: embed user question -> find top-k similar chunks
- [x] Support filtering by store_id (multi-tenant)
- [x] Return chunks with metadata (source, title, URL)
- [x] Implement relevance threshold (discard low-similarity results)

**Function signature:**

```python
async def retrieve_context(
    query: str,
    store_id: UUID,
    top_k: int = 5,
    threshold: float = 0.7
) -> list[RetrievedChunk]:
    ...
```

### 1.3 LLM Response Generation

**Location:** `apps/api/app/services/chat_service.py`

- [x] Create chat service that orchestrates RAG + LLM
- [x] Build system prompt for e-commerce Q&A
- [x] Include retrieved context in prompt
- [x] Use OpenAI GPT-4o for response generation
- [x] Implement conversation memory (last N messages)

**System prompt structure:**

```
You are a helpful customer support agent for {store_name}.
Use the following context to answer the customer's question.
If you don't know the answer, say so - don't make things up.

Context:
{retrieved_chunks}

Conversation history:
{last_n_messages}
```

### 1.4 Citation Parsing

**Location:** `apps/api/app/services/citation_service.py`

- [x] Extract source references from retrieved chunks
- [x] Map citations to original knowledge sources
- [x] Format citations with snippets
- [x] Return structured response with `sources` array

**Response format:**

```json
{
  "message": "We ship to Canada! Standard shipping takes 5-7 business days.",
  "sources": [
    {
      "title": "Shipping Policy",
      "url": "/pages/shipping",
      "snippet": "We ship to Canada, USA, and UK..."
    }
  ]
}
```

### 1.5 Chat API Endpoint

**Location:** `apps/api/app/api/v1/chat.py`

- [x] `POST /api/v1/chat/messages` - Send message, get response
- [x] Create conversation if new session
- [x] Store messages in database
- [x] Return AI response with citations

**Request:**

```json
{
  "conversation_id": "optional-uuid",
  "message": "Do you ship to Canada?",
  "context": {
    "page_url": "/products/winter-jacket",
    "product_id": "prod_123"
  }
}
```

**Response:**

```json
{
  "conversation_id": "uuid",
  "message_id": "uuid",
  "response": "We ship to Canada! ...",
  "sources": [...],
  "created_at": "2026-01-24T10:00:00Z"
}
```

### 1.6 Conversation Persistence

**Location:** `apps/api/app/services/chat_service.py`

- [x] Create conversation on first message
- [x] Store all messages (user + assistant)
- [x] Track conversation metadata (store_id, customer info)
- [x] Support anonymous conversations (no auth required)

---

## Files Created/Modified

| File                                      | Action   | Purpose                        |
| ----------------------------------------- | -------- | ------------------------------ |
| `app/services/embedding_service.py`       | Created  | OpenAI embedding + chunking    |
| `app/services/knowledge_service.py`       | Created  | Knowledge CRUD + ingestion     |
| `app/services/retrieval_service.py`       | Created  | Vector similarity search       |
| `app/services/citation_service.py`        | Created  | Citation formatting            |
| `app/services/chat_service.py`            | Created  | Chat orchestration + RAG       |
| `app/api/v1/knowledge.py`                 | Created  | Knowledge management endpoints |
| `app/api/v1/chat.py`                      | Created  | Chat endpoints                 |
| `app/schemas/knowledge.py`                | Created  | Pydantic models for knowledge  |
| `app/schemas/chat.py`                     | Created  | Pydantic models for chat       |
| `app/workers/tasks/embedding.py`          | Created  | Async embedding Celery task    |
| `app/workers/celery_app.py`               | Modified | Added embedding task           |
| `app/api/v1/router.py`                    | Modified | Registered new routes          |
| `app/models/knowledge.py`                 | Modified | Added token_count field        |
| `alembic/versions/..._add_token_count.py` | Created  | Migration for token_count      |
| `tests/test_embedding_service.py`         | Created  | Embedding service unit tests   |
| `tests/test_citation_service.py`          | Created  | Citation service unit tests    |

---

## Dependencies

```toml
# Added to pyproject.toml
openai = ">=1.59.0"
tiktoken = ">=0.8.0"
pypdf = ">=5.0.0"      # For future PDF support
```

---

## Testing

- [x] Unit test: chunking produces correct sizes
- [x] Unit test: citation formatting works correctly
- [ ] Integration test: full RAG flow (requires running DB)
- [ ] Test: citation extraction accuracy (requires API key)

---

## Acceptance Criteria

1. [x] Can upload a text document and have it chunked + embedded
2. [x] Can ask a question and get a relevant answer
3. [x] Response includes accurate source citations
4. [x] Conversation history is persisted
5. [x] Multi-tenant: each store only sees their own knowledge

---

## Deferred to Later Phases

- **PDF ingestion**: `pypdf` dependency added, implementation deferred
- **URL ingestion**: Will use `httpx` (already installed)
- **Streaming responses**: TODO comments added in `chat_service.py`
- **Embedding caching**: Consider for optimization phase

---

## API Endpoints

### Knowledge Management (Authenticated)

| Method   | Endpoint                 | Description             |
| -------- | ------------------------ | ----------------------- |
| `POST`   | `/api/v1/knowledge`      | Ingest document         |
| `GET`    | `/api/v1/knowledge`      | List articles           |
| `GET`    | `/api/v1/knowledge/{id}` | Get article with chunks |
| `PATCH`  | `/api/v1/knowledge/{id}` | Update article metadata |
| `DELETE` | `/api/v1/knowledge/{id}` | Delete article          |

### Chat (Unauthenticated - Widget)

| Method | Endpoint                          | Description                 |
| ------ | --------------------------------- | --------------------------- |
| `POST` | `/api/v1/chat/messages`           | Send message, get AI response |
| `GET`  | `/api/v1/chat/conversations/{id}` | Get conversation history    |
| `GET`  | `/api/v1/chat/conversations`      | List by session ID          |

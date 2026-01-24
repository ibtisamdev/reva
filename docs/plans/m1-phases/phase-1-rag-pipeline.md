# Phase 1: Core AI/RAG Pipeline

> **Parent:** [M1 Product Q&A Bot](../m1-product-qa.md)  
> **Duration:** 1.5 weeks  
> **Status:** Not Started

---

## Goal

Build the knowledge ingestion pipeline and RAG (Retrieval-Augmented Generation) system that powers AI responses.

---

## Tasks

### 1.1 Knowledge Ingestion Service

**Location:** `apps/api/app/knowledge/ingestion.py`

- [ ] Create document ingestion endpoint `POST /api/v1/knowledge`
- [ ] Implement text chunking (512 tokens, 50 token overlap)
- [ ] Support multiple input types:
  - [ ] Plain text
  - [ ] PDF files (using `pypdf` or `pdfplumber`)
  - [ ] URLs (fetch and extract text)
- [ ] Generate embeddings using OpenAI `text-embedding-3-small`
- [ ] Store chunks + embeddings in `knowledge_chunks` table (pgvector)
- [ ] Handle large documents async via Celery task

**Database Schema:**

```sql
-- Already exists in knowledge table, but may need:
ALTER TABLE knowledge ADD COLUMN chunk_index INTEGER;
ALTER TABLE knowledge ADD COLUMN token_count INTEGER;
```

### 1.2 RAG Retrieval Service

**Location:** `apps/api/app/knowledge/retrieval.py`

- [ ] Implement vector similarity search using pgvector
- [ ] Query: embed user question -> find top-k similar chunks
- [ ] Support filtering by store_id (multi-tenant)
- [ ] Return chunks with metadata (source, title, URL)
- [ ] Implement relevance threshold (discard low-similarity results)

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

**Location:** `apps/api/app/services/chat.py`

- [ ] Create chat service that orchestrates RAG + LLM
- [ ] Build system prompt for e-commerce Q&A
- [ ] Include retrieved context in prompt
- [ ] Use OpenAI GPT-4o for response generation
- [ ] Implement conversation memory (last N messages)

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

**Location:** `apps/api/app/services/citations.py`

- [ ] Extract source references from LLM response
- [ ] Map citations to original knowledge sources
- [ ] Format citations with clickable links
- [ ] Return structured response with `sources` array

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

- [ ] `POST /api/v1/chat/messages` - Send message, get response
- [ ] Create conversation if new session
- [ ] Store messages in database
- [ ] Return AI response with citations

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

**Location:** `apps/api/app/services/conversation.py`

- [ ] Create conversation on first message
- [ ] Store all messages (user + assistant)
- [ ] Track conversation metadata (store_id, customer info)
- [ ] Support anonymous conversations (no auth required)

---

## Files to Create/Modify

| File                             | Action | Purpose                       |
| -------------------------------- | ------ | ----------------------------- |
| `app/knowledge/__init__.py`      | Create | Package init                  |
| `app/knowledge/ingestion.py`     | Create | Document processing           |
| `app/knowledge/retrieval.py`     | Create | Vector search                 |
| `app/knowledge/embeddings.py`    | Create | OpenAI embedding wrapper      |
| `app/services/chat.py`           | Create | Chat orchestration            |
| `app/services/citations.py`      | Create | Citation parsing              |
| `app/services/conversation.py`   | Create | Conversation management       |
| `app/api/v1/chat.py`             | Create | Chat endpoints                |
| `app/api/v1/knowledge.py`        | Create | Knowledge upload endpoints    |
| `app/schemas/chat.py`            | Create | Pydantic models for chat      |
| `app/schemas/knowledge.py`       | Create | Pydantic models for knowledge |
| `app/workers/knowledge_tasks.py` | Create | Async ingestion tasks         |

---

## Dependencies

```toml
# Add to pyproject.toml
openai = "^1.0"
tiktoken = "^0.5"      # Token counting
pypdf = "^4.0"         # PDF parsing
httpx = "^0.27"        # URL fetching
```

---

## Testing

- [ ] Unit test: chunking produces correct sizes
- [ ] Unit test: embeddings are generated correctly
- [ ] Unit test: retrieval returns relevant chunks
- [ ] Integration test: full RAG flow (ingest -> query -> response)
- [ ] Test: citation extraction accuracy

---

## Acceptance Criteria

1. Can upload a text document and have it chunked + embedded
2. Can ask a question and get a relevant answer
3. Response includes accurate source citations
4. Conversation history is persisted
5. Multi-tenant: each store only sees their own knowledge

---

## Notes

- Start with text-only ingestion, add PDF/URL support iteratively
- Use streaming responses later (Phase 2 enhancement)
- Consider caching embeddings for frequently asked questions

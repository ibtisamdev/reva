# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Widget API Integration** (Phase 2 of M1)
  - Connected chat widget to backend API with session persistence and error handling
  - Citation display for AI responses with source links
  - Theme customization via `window.RevaConfig` for store branding

- **RAG Pipeline** (Phase 1 of M1)
  - Knowledge ingestion service with automatic text chunking (512 tokens, 50 token overlap)
  - OpenAI `text-embedding-3-small` embeddings (1536 dimensions)
  - pgvector similarity search for semantic retrieval
  - Chat service with GPT-4o response generation
  - Citation extraction with source snippets
  - Conversation persistence with message history
  - Async embedding processing via Celery for large documents

- **API Endpoints**
  - `POST /api/v1/knowledge` - Ingest documents with automatic chunking and embedding
  - `GET /api/v1/knowledge` - List knowledge articles with pagination
  - `GET /api/v1/knowledge/{id}` - Get article details with chunks
  - `PATCH /api/v1/knowledge/{id}` - Update article metadata
  - `DELETE /api/v1/knowledge/{id}` - Delete article and chunks
  - `POST /api/v1/chat/messages` - Send message and get AI response with sources
  - `GET /api/v1/chat/conversations/{id}` - Get conversation history
  - `GET /api/v1/chat/conversations` - List conversations by session

- **Database**
  - Migration `73487033ba80`: Added `token_count` column to `knowledge_chunks` table

- **Dependencies**
  - `openai>=1.59.0` - OpenAI API client
  - `tiktoken>=0.8.0` - Token counting for chunking
  - `pypdf>=5.0.0` - PDF parsing (for future use)

### Changed

- Widget styles aligned with design system (teal primary)
- Updated `app/api/v1/router.py` to register knowledge and chat routes
- Updated `app/workers/celery_app.py` to include embedding task module

## [0.1.0] - 2026-01-24

### Added

- Initial project setup with FastAPI backend
- Multi-store architecture with Better Auth integration
- SQLAlchemy models for Store, Product, KnowledgeArticle, KnowledgeChunk, Conversation, Message
- pgvector extension for vector embeddings
- Celery worker infrastructure with Redis
- Health check endpoints
- JWT authentication via Better Auth JWKS

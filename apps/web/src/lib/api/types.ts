/**
 * API Types - Matching backend Pydantic schemas
 */

// === Enums ===

export type ContentType = 'faq' | 'policy' | 'guide' | 'page';
export type Channel = 'widget' | 'email' | 'whatsapp' | 'sms';
export type ConversationStatus = 'active' | 'resolved' | 'escalated';
export type MessageRole = 'user' | 'assistant' | 'system';

// === Common ===

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface ErrorResponse {
  error: string;
  detail?: string;
  code?: string;
}

// === Knowledge ===

export interface KnowledgeChunk {
  id: string;
  chunk_index: number;
  content: string;
  token_count: number | null;
  has_embedding: boolean;
}

export interface KnowledgeArticle {
  id: string;
  store_id: string;
  title: string;
  content: string;
  content_type: ContentType;
  source_url: string | null;
  chunks_count: number;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeArticleDetail extends KnowledgeArticle {
  chunks: KnowledgeChunk[];
}

export interface CreateKnowledgeRequest {
  title: string;
  content: string;
  content_type: ContentType;
  source_url?: string;
}

export interface UpdateKnowledgeRequest {
  title?: string;
  content?: string;
  content_type?: ContentType;
  source_url?: string;
}

export interface IngestionResponse {
  article_id: string;
  title: string;
  chunks_count: number;
  status: 'completed' | 'processing';
  message: string;
}

// === Chat / Conversations ===

export interface SourceReference {
  title: string;
  url: string | null;
  snippet: string;
  chunk_id: string | null;
}

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  sources: SourceReference[] | null;
  tokens_used: number | null;
  created_at: string;
}

export interface Conversation {
  id: string;
  store_id: string;
  session_id: string;
  channel: Channel;
  status: ConversationStatus;
  customer_email: string | null;
  customer_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface ConversationDetail extends Conversation {
  messages: Message[];
}

export interface ChatRequest {
  conversation_id?: string;
  message: string;
  session_id?: string;
  context?: Record<string, unknown>;
}

export interface ChatResponse {
  conversation_id: string;
  message_id: string;
  response: string;
  sources: SourceReference[];
  created_at: string;
}

// === Store ===

export interface Store {
  id: string;
  organization_id: string;
  name: string;
  email: string | null;
  plan: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface StoreListResponse {
  items: Store[];
  total: number;
}

export interface CreateStoreRequest {
  name: string;
  email?: string;
}

export interface UpdateStoreRequest {
  name?: string;
  email?: string;
  is_active?: boolean;
}

// === Store Settings ===

export interface WidgetSettings {
  primary_color: string;
  welcome_message: string;
  position: 'bottom-right' | 'bottom-left';
  agent_name: string;
}

export interface StoreSettings {
  widget: WidgetSettings;
}

export interface UpdateStoreSettingsRequest {
  widget?: Partial<WidgetSettings>;
}

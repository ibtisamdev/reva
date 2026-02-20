/**
 * Centralized TypeScript interfaces for the Reva Widget.
 * These types align with the backend API schemas in apps/api/app/schemas/chat.py
 */

// === API Types (matching backend schemas) ===

/**
 * A source citation from RAG responses.
 * Matches: app/schemas/chat.py::SourceReference
 */
export interface SourceReference {
  title: string;
  url: string | null;
  snippet: string;
  chunk_id: string | null;
}

/**
 * A product card extracted from tool results.
 * Matches: app/schemas/chat.py::ProductCard
 */
export interface Product {
  product_id: string;
  title: string;
  price: string | null;
  image_url: string | null;
  in_stock: boolean;
  product_url: string | null;
}

/**
 * Request payload for sending a chat message.
 * Matches: app/schemas/chat.py::ChatRequest
 */
export interface ChatRequest {
  conversation_id: string | null;
  message: string;
  session_id: string | null;
  context: PageContext | null;
}

/**
 * Response from the chat endpoint.
 * Matches: app/schemas/chat.py::ChatResponse
 */
export interface ChatResponse {
  conversation_id: string;
  message_id: string;
  response: string;
  sources: SourceReference[];
  products: Product[];
  created_at: string;
}

/**
 * A single message in a conversation.
 * Matches: app/schemas/chat.py::MessageResponse
 */
export interface MessageResponse {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  sources: SourceReference[] | null;
  products: Product[] | null;
  tokens_used: number | null;
  created_at: string;
}

/**
 * Full conversation with messages.
 * Matches: app/schemas/chat.py::ConversationDetailResponse
 */
export interface ConversationDetailResponse {
  id: string;
  store_id: string;
  session_id: string;
  channel: 'widget' | 'email' | 'whatsapp' | 'sms';
  status: 'active' | 'resolved' | 'escalated';
  customer_email: string | null;
  customer_name: string | null;
  created_at: string;
  updated_at: string;
  messages: MessageResponse[];
}

// === Widget Types ===

/**
 * Message displayed in the chat UI.
 * Extended from API types with streaming support.
 */
export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: SourceReference[];
  products?: Product[];
  isStreaming?: boolean;
}

/**
 * Page context sent with each message for contextual responses.
 */
export interface PageContext {
  page_url: string;
  page_title: string;
  product_id?: string;
  product_handle?: string;
}

/**
 * Theme customization options for store owners.
 */
export interface WidgetTheme {
  primaryColor?: string;
  // Future expansion:
  // accentColor?: string;
  // fontFamily?: string;
  // borderRadius?: 'sm' | 'md' | 'lg';
}

/**
 * Widget configuration from embed script.
 */
export interface WidgetConfig {
  storeId: string;
  apiUrl?: string;
  theme?: WidgetTheme;
  position?: 'left' | 'right';
  // Future expansion:
  // headerTitle?: string;
  // welcomeMessage?: string;
  // agentAvatar?: string;
}

// === Error Handling Types ===

/**
 * Types of API errors that can occur.
 */
export type ApiErrorType =
  | 'network_error' // API unreachable
  | 'rate_limited' // Too many requests (429)
  | 'server_error' // 500+ errors
  | 'invalid_response' // Malformed response
  | 'store_not_found' // Store doesn't exist (404)
  | 'not_configured'; // Widget not configured (missing storeId)

/**
 * Structured API error with retry information.
 */
export interface ApiError {
  type: ApiErrorType;
  message: string;
  retryable: boolean;
}

// === Recovery Types ===

/**
 * A cart item in a recovery popup.
 */
export interface RecoveryItem {
  title: string;
  price: string;
  image_url: string | null;
  quantity: number;
}

/**
 * Response from the recovery check endpoint.
 */
export interface RecoveryCheckResponse {
  has_recovery: boolean;
  items: RecoveryItem[];
  checkout_url: string | null;
  total_price: string | null;
  sequence_id: string | null;
}

// === Global Window Extension ===

declare global {
  interface Window {
    RevaConfig?: Partial<WidgetConfig>;
  }
}

/**
 * API client for the Reva Widget.
 * Handles chat API calls with error handling and retry logic.
 */

import type {
  ApiError,
  ApiErrorType,
  ChatRequest,
  ChatResponse,
  ConversationDetailResponse,
  RecoveryCheckResponse,
} from '../types';

// === Constants ===

const MAX_RETRIES = 2;
const RETRY_DELAY_MS = 1000;

// === Error Handling ===

/**
 * Create a structured API error.
 */
function createError(type: ApiErrorType, message: string, retryable: boolean): ApiError {
  return { type, message, retryable };
}

/**
 * Type guard to check if a result is an ApiError.
 */
export function isApiError(result: unknown): result is ApiError {
  return (
    typeof result === 'object' &&
    result !== null &&
    'type' in result &&
    'message' in result &&
    'retryable' in result
  );
}

/**
 * Parse error message from API response.
 * FastAPI returns errors in format: {"detail": "message"} or {"detail": [{"msg": "message"}]}
 */
function parseErrorMessage(responseText: string): string {
  try {
    const parsed = JSON.parse(responseText);

    // Handle FastAPI validation errors: {"detail": [{"msg": "...", "type": "..."}]}
    if (Array.isArray(parsed.detail)) {
      const firstError = parsed.detail[0];
      if (firstError?.msg) {
        // Make the message more user-friendly
        if (firstError.type === 'uuid_parsing' || firstError.msg.includes('UUID')) {
          return 'Invalid store configuration. Please contact support.';
        }
        return firstError.msg;
      }
    }

    // Handle simple error: {"detail": "message"}
    if (typeof parsed.detail === 'string') {
      return parsed.detail;
    }

    return 'An error occurred. Please try again.';
  } catch {
    // Not JSON, return generic message
    return 'An error occurred. Please try again.';
  }
}

/**
 * Map HTTP status codes to error types.
 */
function getErrorFromStatus(status: number, responseText: string): ApiError {
  const message = parseErrorMessage(responseText);

  switch (status) {
    case 404:
      return createError('store_not_found', 'Store not found or inactive.', false);
    case 429:
      return createError('rate_limited', 'Too many requests. Please wait a moment.', true);
    case 422:
      return createError('invalid_response', message, false);
    default:
      if (status >= 500) {
        return createError('server_error', 'Server error. Please try again.', true);
      }
      return createError('invalid_response', message, false);
  }
}

// === API Functions ===

/**
 * Sleep for a given number of milliseconds.
 */
function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Make a fetch request with retry logic.
 */
async function fetchWithRetry<T>(
  url: string,
  options: RequestInit,
  retries: number = MAX_RETRIES
): Promise<T | ApiError> {
  let lastError: ApiError | null = null;

  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const response = await fetch(url, options);

      if (!response.ok) {
        const responseText = await response.text().catch(() => '');
        const error = getErrorFromStatus(response.status, responseText);

        // If not retryable or last attempt, return the error
        if (!error.retryable || attempt === retries) {
          return error;
        }

        lastError = error;
        await sleep(RETRY_DELAY_MS * (attempt + 1)); // Exponential backoff
        continue;
      }

      // Parse JSON response
      try {
        return (await response.json()) as T;
      } catch {
        return createError('invalid_response', 'Invalid response format from server.', false);
      }
    } catch (error) {
      // Network error (fetch failed)
      const networkError = createError(
        'network_error',
        'Unable to connect. Please check your internet connection.',
        true
      );

      if (attempt === retries) {
        return networkError;
      }

      lastError = networkError;
      await sleep(RETRY_DELAY_MS * (attempt + 1));
    }
  }

  // Should not reach here, but return last error just in case
  return lastError || createError('network_error', 'Request failed.', true);
}

/**
 * Send a chat message and receive an AI response.
 *
 * @param apiUrl - Base API URL
 * @param storeId - Store identifier
 * @param request - Chat request payload
 * @returns ChatResponse on success, ApiError on failure
 */
export async function sendMessage(
  apiUrl: string,
  storeId: string,
  request: ChatRequest
): Promise<ChatResponse | ApiError> {
  const url = `${apiUrl}/api/v1/chat/messages?store_id=${encodeURIComponent(storeId)}`;

  return fetchWithRetry<ChatResponse>(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
}

/**
 * Get a conversation with all its messages.
 *
 * @param apiUrl - Base API URL
 * @param storeId - Store identifier
 * @param conversationId - Conversation UUID
 * @returns ConversationDetailResponse on success, ApiError on failure
 */
export async function getConversation(
  apiUrl: string,
  storeId: string,
  conversationId: string
): Promise<ConversationDetailResponse | ApiError> {
  const url = `${apiUrl}/api/v1/chat/conversations/${encodeURIComponent(conversationId)}?store_id=${encodeURIComponent(storeId)}`;

  return fetchWithRetry<ConversationDetailResponse>(url, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });
}

/**
 * Get all conversations for a session (returning user).
 *
 * @param apiUrl - Base API URL
 * @param storeId - Store identifier
 * @param sessionId - Session identifier
 * @returns Array of ConversationDetailResponse on success, ApiError on failure
 */
export async function getConversationsBySession(
  apiUrl: string,
  storeId: string,
  sessionId: string
): Promise<ConversationDetailResponse[] | ApiError> {
  const url = `${apiUrl}/api/v1/chat/conversations?store_id=${encodeURIComponent(storeId)}&session_id=${encodeURIComponent(sessionId)}`;

  return fetchWithRetry<ConversationDetailResponse[]>(url, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });
}

/**
 * Check if the current session has an active cart recovery.
 *
 * @param apiUrl - Base API URL
 * @param storeId - Store identifier
 * @param sessionId - Session identifier
 * @returns RecoveryCheckResponse on success, ApiError on failure
 */
export async function checkRecovery(
  apiUrl: string,
  storeId: string,
  sessionId: string
): Promise<RecoveryCheckResponse | ApiError> {
  const url = `${apiUrl}/api/v1/recovery/check?store_id=${encodeURIComponent(storeId)}&session_id=${encodeURIComponent(sessionId)}`;

  return fetchWithRetry<RecoveryCheckResponse>(url, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });
}

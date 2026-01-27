/**
 * Session management for the Reva Widget.
 * Handles persistence of session ID (user identity) and conversation ID (current chat).
 */

const SESSION_KEY = 'reva_session_id';
const CONVERSATION_KEY = 'reva_conversation_id';

// === Session ID ===
// Persistent user identity across conversations and page visits.

/**
 * Get or create a session ID.
 * Session ID persists across page refreshes and browser sessions.
 * Used to link multiple conversations to the same anonymous user.
 */
export function getSessionId(): string {
  try {
    let sessionId = localStorage.getItem(SESSION_KEY);
    if (!sessionId) {
      sessionId = crypto.randomUUID();
      localStorage.setItem(SESSION_KEY, sessionId);
    }
    return sessionId;
  } catch {
    // localStorage unavailable (e.g., private browsing in some browsers)
    // Generate a temporary session ID for this page visit
    return crypto.randomUUID();
  }
}

// === Conversation ID ===
// Current active conversation, persists across page navigations.

/**
 * Get the current conversation ID.
 * Returns null if no active conversation.
 */
export function getConversationId(): string | null {
  try {
    return localStorage.getItem(CONVERSATION_KEY);
  } catch {
    return null;
  }
}

/**
 * Set the current conversation ID.
 * Called after the first message creates a new conversation.
 */
export function setConversationId(id: string): void {
  try {
    localStorage.setItem(CONVERSATION_KEY, id);
  } catch {
    // Ignore if localStorage is unavailable
  }
}

/**
 * Clear the conversation ID to start a new conversation.
 * Called when user clicks "New conversation" or manually clears.
 */
export function clearConversation(): void {
  try {
    localStorage.removeItem(CONVERSATION_KEY);
  } catch {
    // Ignore if localStorage is unavailable
  }
}

/**
 * Clear all Reva session data.
 * Useful for "reset" functionality.
 */
export function clearAllSessionData(): void {
  try {
    localStorage.removeItem(SESSION_KEY);
    localStorage.removeItem(CONVERSATION_KEY);
  } catch {
    // Ignore if localStorage is unavailable
  }
}

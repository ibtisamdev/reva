/**
 * ChatWindow component - the main chat interface.
 * Handles message sending, API integration, and conversation state.
 */

import { useState, useRef, useEffect } from 'preact/hooks';

import type { ApiError, Message } from '../types';
import { sendMessage, isApiError } from '../lib/api';
import { getPageContext } from '../lib/context';
import { getSessionId, getConversationId, setConversationId } from '../lib/session';
import { ChatMessage } from './ChatMessage';

interface ChatWindowProps {
  storeId: string;
  apiUrl?: string;
  onClose: () => void;
}

export function ChatWindow({ storeId, apiUrl = 'http://localhost:8000', onClose }: ChatWindowProps) {
  // Message state
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: 'Hi! How can I help you today?',
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  // Conversation state - initialized from localStorage
  const [conversationId, setConversationIdState] = useState<string | null>(() =>
    getConversationId()
  );

  // Ref for auto-scroll
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  /**
   * Handle form submission - send message to API.
   */
  const handleSubmit = async (e: Event) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    // Create user message
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
    };

    // Update UI immediately
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    setError(null);

    // Send to API
    const result = await sendMessage(apiUrl, storeId, {
      conversation_id: conversationId,
      message: userMessage.content,
      session_id: getSessionId(),
      context: getPageContext(),
    });

    // Handle API error
    if (isApiError(result)) {
      setError(result);
      setIsLoading(false);
      return;
    }

    // Save conversation ID for follow-up messages
    if (!conversationId) {
      setConversationIdState(result.conversation_id);
      setConversationId(result.conversation_id);
    }

    // Add assistant response
    const assistantMessage: Message = {
      id: result.message_id,
      role: 'assistant',
      content: result.response,
      sources: result.sources,
    };

    setMessages((prev) => [...prev, assistantMessage]);
    setIsLoading(false);
  };

  /**
   * Retry the last failed message.
   */
  const handleRetry = () => {
    // Find the last user message
    const lastUserMessage = [...messages].reverse().find((m) => m.role === 'user');
    if (lastUserMessage) {
      // Remove the last user message and retry
      setMessages((prev) => prev.filter((m) => m.id !== lastUserMessage.id));
      setInput(lastUserMessage.content);
      setError(null);
    }
  };

  return (
    <div className="reva-chat-window">
      {/* Header */}
      <div className="reva-header">
        <div className="reva-header-avatar">
          <svg width="20" height="20" viewBox="0 0 24 24">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z" />
          </svg>
        </div>
        <div className="reva-header-info">
          <h3>Reva Support</h3>
          <p>We typically reply instantly</p>
        </div>
        <button
          className="reva-close-button"
          onClick={onClose}
          aria-label="Close chat"
          style={{
            background: 'transparent',
            border: 'none',
            cursor: 'pointer',
            padding: '4px',
            marginLeft: 'auto',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" style={{ opacity: 0.8 }}>
            <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z" />
          </svg>
        </button>
      </div>

      {/* Messages */}
      <div className="reva-messages">
        {messages.map((message) => (
          <ChatMessage key={message.id} message={message} />
        ))}

        {/* Loading indicator */}
        {isLoading && (
          <div className="reva-typing">
            <span></span>
            <span></span>
            <span></span>
          </div>
        )}

        {/* Error message */}
        {error && (
          <div className="reva-error" role="alert">
            <svg className="reva-error-icon" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z" />
            </svg>
            <span className="reva-error-message">{error.message}</span>
            {error.retryable && (
              <button className="reva-error-retry" onClick={handleRetry}>
                Retry
              </button>
            )}
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form className="reva-input-container" onSubmit={handleSubmit}>
        <input
          type="text"
          className="reva-input"
          placeholder="Type a message..."
          value={input}
          onInput={(e) => setInput((e.target as HTMLInputElement).value)}
          disabled={isLoading}
          aria-label="Message input"
        />
        <button
          type="submit"
          className="reva-send-button"
          disabled={!input.trim() || isLoading}
          aria-label="Send message"
        >
          <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
          </svg>
        </button>
      </form>
    </div>
  );
}

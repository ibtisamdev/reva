/**
 * ChatMessage component for the Reva Widget.
 * Renders a single message with optional streaming cursor and citations.
 */

import type { Message } from '../types';

interface ChatMessageProps {
  message: Message;
}

/**
 * Render a single chat message.
 * Supports streaming state and citation display for assistant messages.
 */
export function ChatMessage({ message }: ChatMessageProps) {
  const { role, content, sources, isStreaming } = message;
  const isAssistant = role === 'assistant';
  const hasSources = isAssistant && sources && sources.length > 0;

  return (
    <div className={`reva-message reva-message-${role}`}>
      {/* Message content */}
      <div className="reva-message-content">
        {content}
        {isStreaming && <span className="reva-cursor" aria-hidden="true" />}
      </div>

      {/* Citations - only for assistant messages with sources */}
      {hasSources && (
        <div className="reva-sources">
          <span className="reva-sources-label">Sources:</span>
          <div className="reva-sources-list">
            {sources.map((source, index) => (
              <a
                key={source.chunk_id || index}
                href={source.url || '#'}
                target={source.url ? '_blank' : undefined}
                rel={source.url ? 'noopener noreferrer' : undefined}
                className="reva-source-link"
                title={source.snippet}
                onClick={(e) => {
                  // Prevent navigation if no URL
                  if (!source.url) {
                    e.preventDefault();
                  }
                }}
              >
                {source.title}
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

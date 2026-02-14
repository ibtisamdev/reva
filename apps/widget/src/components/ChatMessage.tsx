/**
 * ChatMessage component for the Reva Widget.
 * Renders a single message with optional streaming cursor, citations, and product cards.
 * Assistant messages are rendered as markdown; user messages remain plain text.
 */

import { renderMarkdown } from '../lib/markdown';
import type { Message } from '../types';
import { ProductCard } from './ProductCard';

interface ChatMessageProps {
  message: Message;
}

/**
 * Render a single chat message.
 * Supports streaming state, citation display, and product card grid for assistant messages.
 */
export function ChatMessage({ message }: ChatMessageProps) {
  const { role, content, sources, products, isStreaming } = message;
  const isAssistant = role === 'assistant';
  const hasSources = isAssistant && sources && sources.length > 0;
  const hasProducts = isAssistant && products && products.length > 0;

  return (
    <div className={`reva-message reva-message-${role}`}>
      {/* Message content */}
      {isAssistant ? (
        <div className="reva-message-content reva-markdown">
          <div dangerouslySetInnerHTML={{ __html: renderMarkdown(content) }} />
          {isStreaming && <span className="reva-cursor" aria-hidden="true" />}
        </div>
      ) : (
        <div className="reva-message-content">{content}</div>
      )}

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

      {/* Product cards grid - outside the message bubble */}
      {hasProducts && (
        <div className="reva-products-grid">
          {products.map((product) => (
            <ProductCard key={product.product_id} product={product} />
          ))}
        </div>
      )}
    </div>
  );
}

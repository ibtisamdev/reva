import { useState, useRef, useEffect } from 'preact/hooks';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
}

interface ChatWindowProps {
  organizationId: string;
  onClose: () => void;
}

export function ChatWindow({ organizationId, onClose: _onClose }: ChatWindowProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: 'Hi! How can I help you today?',
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = async (e: Event) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    // TODO: Replace with actual API call
    // Simulating API response for now
    setTimeout(() => {
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `Thanks for your message! This is a demo response. In production, this will be powered by AI. (Org: ${organizationId})`,
      };
      setMessages((prev) => [...prev, assistantMessage]);
      setIsLoading(false);
    }, 1000);
  };

  return (
    <div className="reva-chat-window">
      <div className="reva-header">
        <div className="reva-header-avatar">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="white">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z" />
          </svg>
        </div>
        <div className="reva-header-info">
          <h3>Reva Support</h3>
          <p>We typically reply instantly</p>
        </div>
      </div>

      <div className="reva-messages">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`reva-message reva-message-${message.role}`}
          >
            {message.content}
          </div>
        ))}
        {isLoading && (
          <div className="reva-typing">
            <span></span>
            <span></span>
            <span></span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form className="reva-input-container" onSubmit={handleSubmit}>
        <input
          type="text"
          className="reva-input"
          placeholder="Type a message..."
          value={input}
          onInput={(e) => setInput((e.target as HTMLInputElement).value)}
          disabled={isLoading}
        />
        <button
          type="submit"
          className="reva-send-button"
          disabled={!input.trim() || isLoading}
        >
          <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
          </svg>
        </button>
      </form>
    </div>
  );
}

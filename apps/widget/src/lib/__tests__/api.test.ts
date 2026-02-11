import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { ChatRequest } from '../../types';
import { getConversation, getConversationsBySession, isApiError, sendMessage } from '../api';

// Helper to create a valid ChatRequest
function createChatRequest(message: string, overrides: Partial<ChatRequest> = {}): ChatRequest {
  return {
    message,
    conversation_id: null,
    session_id: 'test-session-id',
    context: null,
    ...overrides,
  };
}

describe('isApiError', () => {
  it('returns true for valid ApiError objects', () => {
    const error = { type: 'network_error', message: 'Failed', retryable: true };
    expect(isApiError(error)).toBe(true);
  });

  it('returns true for store_not_found error', () => {
    const error = { type: 'store_not_found', message: 'Store not found', retryable: false };
    expect(isApiError(error)).toBe(true);
  });

  it('returns true for rate_limited error', () => {
    const error = { type: 'rate_limited', message: 'Too many requests', retryable: true };
    expect(isApiError(error)).toBe(true);
  });

  it('returns false for objects missing type property', () => {
    expect(isApiError({ message: 'error', retryable: true })).toBe(false);
  });

  it('returns false for objects missing message property', () => {
    expect(isApiError({ type: 'error', retryable: true })).toBe(false);
  });

  it('returns false for objects missing retryable property', () => {
    expect(isApiError({ type: 'error', message: 'error' })).toBe(false);
  });

  it('returns false for null', () => {
    expect(isApiError(null)).toBe(false);
  });

  it('returns false for undefined', () => {
    expect(isApiError(undefined)).toBe(false);
  });

  it('returns false for string', () => {
    expect(isApiError('error')).toBe(false);
  });

  it('returns false for number', () => {
    expect(isApiError(500)).toBe(false);
  });

  it('returns false for regular response objects', () => {
    expect(isApiError({ response: 'data', conversation_id: '123' })).toBe(false);
  });
});

describe('sendMessage', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('constructs correct URL with encoded store ID', async () => {
    const mockFetch = vi.mocked(fetch);
    mockFetch.mockResolvedValue(
      new Response(
        JSON.stringify({
          conversation_id: 'conv-123',
          message_id: 'msg-456',
          response: 'Hello!',
          sources: [],
          created_at: '2024-01-01T00:00:00Z',
        }),
        { status: 200 }
      )
    );

    const request = createChatRequest('Hello');
    await sendMessage('https://api.example.com', 'store-123', request);

    expect(mockFetch).toHaveBeenCalledWith(
      'https://api.example.com/api/v1/chat/messages?store_id=store-123',
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      })
    );
  });

  it('encodes special characters in store ID', async () => {
    const mockFetch = vi.mocked(fetch);
    mockFetch.mockResolvedValue(new Response(JSON.stringify({ response: 'Hi!' }), { status: 200 }));

    await sendMessage('https://api.example.com', 'store with spaces', createChatRequest('Hello'));

    expect(mockFetch).toHaveBeenCalledWith(
      'https://api.example.com/api/v1/chat/messages?store_id=store%20with%20spaces',
      expect.any(Object)
    );
  });

  it('returns ChatResponse on success', async () => {
    const mockResponse = {
      conversation_id: 'conv-123',
      message_id: 'msg-456',
      response: 'Hello there!',
      sources: [{ title: 'FAQ', url: 'https://example.com/faq', snippet: 'test' }],
      created_at: '2024-01-01T00:00:00Z',
    };

    vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify(mockResponse), { status: 200 }));

    const result = await sendMessage(
      'https://api.example.com',
      'store-123',
      createChatRequest('Hi')
    );

    expect(isApiError(result)).toBe(false);
    expect(result).toEqual(mockResponse);
  });

  it('returns ApiError with type store_not_found on 404', async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response('{"detail":"Store not found"}', { status: 404 })
    );

    const result = await sendMessage(
      'https://api.example.com',
      'store-123',
      createChatRequest('Hi')
    );

    expect(isApiError(result)).toBe(true);
    if (isApiError(result)) {
      expect(result.type).toBe('store_not_found');
      expect(result.retryable).toBe(false);
    }
  });

  it('returns ApiError with type rate_limited on 429', async () => {
    vi.mocked(fetch).mockResolvedValue(new Response('{}', { status: 429 }));

    const result = await sendMessage(
      'https://api.example.com',
      'store-123',
      createChatRequest('Hi')
    );

    expect(isApiError(result)).toBe(true);
    if (isApiError(result)) {
      expect(result.type).toBe('rate_limited');
      expect(result.retryable).toBe(true);
    }
  });

  it('returns ApiError with type invalid_response on 422', async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response('{"detail":"Validation error"}', { status: 422 })
    );

    const result = await sendMessage(
      'https://api.example.com',
      'store-123',
      createChatRequest('Hi')
    );

    expect(isApiError(result)).toBe(true);
    if (isApiError(result)) {
      expect(result.type).toBe('invalid_response');
      expect(result.retryable).toBe(false);
    }
  });

  it('returns ApiError with type server_error on 500', async () => {
    vi.mocked(fetch).mockResolvedValue(new Response('{}', { status: 500 }));

    const result = await sendMessage(
      'https://api.example.com',
      'store-123',
      createChatRequest('Hi')
    );

    expect(isApiError(result)).toBe(true);
    if (isApiError(result)) {
      expect(result.type).toBe('server_error');
      expect(result.retryable).toBe(true);
    }
  });

  it('returns ApiError with type server_error on 503', async () => {
    vi.mocked(fetch).mockResolvedValue(new Response('{}', { status: 503 }));

    const result = await sendMessage(
      'https://api.example.com',
      'store-123',
      createChatRequest('Hi')
    );

    expect(isApiError(result)).toBe(true);
    if (isApiError(result)) {
      expect(result.type).toBe('server_error');
    }
  });

  it('parses FastAPI validation error detail array', async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: [{ msg: 'Field required', type: 'missing', loc: ['body', 'message'] }],
        }),
        { status: 422 }
      )
    );

    const result = await sendMessage('https://api.example.com', 'store-123', createChatRequest(''));

    expect(isApiError(result)).toBe(true);
    if (isApiError(result)) {
      expect(result.message).toBe('Field required');
    }
  });

  it('parses FastAPI UUID parsing error with user-friendly message', async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: [{ msg: 'Invalid UUID format', type: 'uuid_parsing' }],
        }),
        { status: 422 }
      )
    );

    const result = await sendMessage(
      'https://api.example.com',
      'invalid-store',
      createChatRequest('Hi')
    );

    expect(isApiError(result)).toBe(true);
    if (isApiError(result)) {
      expect(result.message).toBe('Invalid store configuration. Please contact support.');
    }
  });

  it('returns network_error on fetch failure', async () => {
    vi.mocked(fetch).mockRejectedValue(new Error('Network failure'));

    const result = await sendMessage(
      'https://api.example.com',
      'store-123',
      createChatRequest('Hi')
    );

    expect(isApiError(result)).toBe(true);
    if (isApiError(result)) {
      expect(result.type).toBe('network_error');
      expect(result.retryable).toBe(true);
    }
  });

  it('returns invalid_response when response is not valid JSON', async () => {
    vi.mocked(fetch).mockResolvedValue(new Response('not json', { status: 200 }));

    const result = await sendMessage(
      'https://api.example.com',
      'store-123',
      createChatRequest('Hi')
    );

    expect(isApiError(result)).toBe(true);
    if (isApiError(result)) {
      expect(result.type).toBe('invalid_response');
    }
  });
});

describe('getConversation', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('constructs correct URL with conversation ID and store ID', async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify({ id: 'conv-123', messages: [] }), { status: 200 })
    );

    await getConversation('https://api.example.com', 'store-1', 'conv-123');

    expect(fetch).toHaveBeenCalledWith(
      'https://api.example.com/api/v1/chat/conversations/conv-123?store_id=store-1',
      expect.objectContaining({
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
      })
    );
  });

  it('encodes special characters in conversation ID', async () => {
    vi.mocked(fetch).mockResolvedValue(new Response('{}', { status: 200 }));

    await getConversation('https://api.example.com', 'store-1', 'conv/with/slashes');

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('conv%2Fwith%2Fslashes'),
      expect.any(Object)
    );
  });

  it('returns ConversationDetailResponse on success', async () => {
    const mockConversation = {
      id: 'conv-123',
      store_id: 'store-1',
      status: 'active',
      messages: [{ id: 'msg-1', role: 'user', content: 'Hello' }],
    };

    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify(mockConversation), { status: 200 })
    );

    const result = await getConversation('https://api.example.com', 'store-1', 'conv-123');

    expect(isApiError(result)).toBe(false);
    expect(result).toEqual(mockConversation);
  });

  it('returns ApiError on 404', async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response('{"detail":"Conversation not found"}', { status: 404 })
    );

    const result = await getConversation('https://api.example.com', 'store-1', 'conv-999');

    expect(isApiError(result)).toBe(true);
    if (isApiError(result)) {
      expect(result.type).toBe('store_not_found');
    }
  });
});

describe('getConversationsBySession', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('includes session_id in query params', async () => {
    vi.mocked(fetch).mockResolvedValue(new Response('[]', { status: 200 }));

    await getConversationsBySession('https://api.example.com', 'store-1', 'session-abc');

    expect(fetch).toHaveBeenCalledWith(
      'https://api.example.com/api/v1/chat/conversations?store_id=store-1&session_id=session-abc',
      expect.any(Object)
    );
  });

  it('encodes special characters in session ID', async () => {
    vi.mocked(fetch).mockResolvedValue(new Response('[]', { status: 200 }));

    await getConversationsBySession('https://api.example.com', 'store-1', 'session with spaces');

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('session_id=session%20with%20spaces'),
      expect.any(Object)
    );
  });

  it('returns array of conversations on success', async () => {
    const mockConversations = [
      { id: 'conv-1', store_id: 'store-1', messages: [] },
      { id: 'conv-2', store_id: 'store-1', messages: [] },
    ];

    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify(mockConversations), { status: 200 })
    );

    const result = await getConversationsBySession(
      'https://api.example.com',
      'store-1',
      'session-abc'
    );

    expect(isApiError(result)).toBe(false);
    expect(Array.isArray(result)).toBe(true);
    expect(result).toHaveLength(2);
  });

  it('returns empty array when no conversations found', async () => {
    vi.mocked(fetch).mockResolvedValue(new Response('[]', { status: 200 }));

    const result = await getConversationsBySession(
      'https://api.example.com',
      'store-1',
      'new-session'
    );

    expect(isApiError(result)).toBe(false);
    expect(result).toEqual([]);
  });

  it('returns ApiError on server error', async () => {
    vi.mocked(fetch).mockResolvedValue(new Response('{}', { status: 500 }));

    const result = await getConversationsBySession(
      'https://api.example.com',
      'store-1',
      'session-abc'
    );

    expect(isApiError(result)).toBe(true);
    if (isApiError(result)) {
      expect(result.type).toBe('server_error');
    }
  });
});

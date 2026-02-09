import { beforeEach, describe, expect, it, vi } from 'vitest';

import {
  clearAllSessionData,
  clearConversation,
  getConversationId,
  getSessionId,
  setConversationId,
} from '../session';

describe('getSessionId', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('creates and stores new session ID when none exists', () => {
    const sessionId = getSessionId();

    expect(sessionId).toBe('mock-uuid-1234-5678-9abc-def012345678');
    expect(localStorage.setItem).toHaveBeenCalledWith(
      'reva_session_id',
      'mock-uuid-1234-5678-9abc-def012345678'
    );
  });

  it('returns existing session ID from localStorage', () => {
    // Pre-set a session ID
    localStorage.setItem('reva_session_id', 'existing-session-id');

    const sessionId = getSessionId();

    expect(sessionId).toBe('existing-session-id');
  });

  it('does not overwrite existing session ID', () => {
    localStorage.setItem('reva_session_id', 'existing-session');

    getSessionId();

    // setItem should have been called once during setup, not again
    expect(localStorage.setItem).toHaveBeenCalledTimes(1);
    expect(localStorage.setItem).toHaveBeenCalledWith('reva_session_id', 'existing-session');
  });

  it('creates new UUID when localStorage is empty', () => {
    // localStorage is already empty from beforeEach

    const sessionId = getSessionId();

    expect(sessionId).toBeTruthy();
    expect(typeof sessionId).toBe('string');
  });
});

describe('getConversationId', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('returns null when no conversation ID exists', () => {
    const conversationId = getConversationId();

    expect(conversationId).toBeNull();
  });

  it('returns stored conversation ID', () => {
    localStorage.setItem('reva_conversation_id', 'conv-123');

    const conversationId = getConversationId();

    expect(conversationId).toBe('conv-123');
  });

  it('calls localStorage.getItem with correct key', () => {
    getConversationId();

    expect(localStorage.getItem).toHaveBeenCalledWith('reva_conversation_id');
  });
});

describe('setConversationId', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('stores conversation ID in localStorage', () => {
    setConversationId('new-conv-456');

    expect(localStorage.setItem).toHaveBeenCalledWith('reva_conversation_id', 'new-conv-456');
  });

  it('overwrites existing conversation ID', () => {
    localStorage.setItem('reva_conversation_id', 'old-conv');

    setConversationId('new-conv');

    expect(localStorage.setItem).toHaveBeenLastCalledWith('reva_conversation_id', 'new-conv');
  });

  it('can be retrieved after setting', () => {
    setConversationId('test-conv-789');

    const retrieved = getConversationId();

    expect(retrieved).toBe('test-conv-789');
  });
});

describe('clearConversation', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('removes conversation ID from localStorage', () => {
    localStorage.setItem('reva_conversation_id', 'conv-to-clear');

    clearConversation();

    expect(localStorage.removeItem).toHaveBeenCalledWith('reva_conversation_id');
  });

  it('conversation ID returns null after clearing', () => {
    localStorage.setItem('reva_conversation_id', 'conv-to-clear');

    clearConversation();

    expect(getConversationId()).toBeNull();
  });

  it('does not affect session ID', () => {
    localStorage.setItem('reva_session_id', 'session-123');
    localStorage.setItem('reva_conversation_id', 'conv-456');

    clearConversation();

    // Session ID should still exist
    expect(localStorage.getItem('reva_session_id')).toBe('session-123');
  });
});

describe('clearAllSessionData', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('removes session ID from localStorage', () => {
    localStorage.setItem('reva_session_id', 'session-to-clear');

    clearAllSessionData();

    expect(localStorage.removeItem).toHaveBeenCalledWith('reva_session_id');
  });

  it('removes conversation ID from localStorage', () => {
    localStorage.setItem('reva_conversation_id', 'conv-to-clear');

    clearAllSessionData();

    expect(localStorage.removeItem).toHaveBeenCalledWith('reva_conversation_id');
  });

  it('removes both session and conversation IDs', () => {
    localStorage.setItem('reva_session_id', 'session-123');
    localStorage.setItem('reva_conversation_id', 'conv-456');

    clearAllSessionData();

    expect(localStorage.removeItem).toHaveBeenCalledWith('reva_session_id');
    expect(localStorage.removeItem).toHaveBeenCalledWith('reva_conversation_id');
  });

  it('getSessionId creates new ID after clearing', () => {
    localStorage.setItem('reva_session_id', 'old-session');

    clearAllSessionData();

    const newSessionId = getSessionId();

    // Should create a new session ID (the mock UUID)
    expect(newSessionId).toBe('mock-uuid-1234-5678-9abc-def012345678');
  });

  it('getConversationId returns null after clearing', () => {
    localStorage.setItem('reva_conversation_id', 'old-conv');

    clearAllSessionData();

    expect(getConversationId()).toBeNull();
  });
});

describe('localStorage error handling', () => {
  it('getSessionId generates temporary ID when localStorage throws', () => {
    // Make localStorage.getItem throw
    vi.mocked(localStorage.getItem).mockImplementation(() => {
      throw new Error('Storage error');
    });

    const sessionId = getSessionId();

    // Should return a generated UUID (from crypto.randomUUID mock)
    expect(sessionId).toBe('mock-uuid-1234-5678-9abc-def012345678');
  });

  it('getConversationId returns null when localStorage throws', () => {
    vi.mocked(localStorage.getItem).mockImplementation(() => {
      throw new Error('Storage error');
    });

    const conversationId = getConversationId();

    expect(conversationId).toBeNull();
  });

  it('setConversationId handles localStorage error gracefully', () => {
    vi.mocked(localStorage.setItem).mockImplementation(() => {
      throw new Error('Storage error');
    });

    // Should not throw
    expect(() => setConversationId('test')).not.toThrow();
  });

  it('clearConversation handles localStorage error gracefully', () => {
    vi.mocked(localStorage.removeItem).mockImplementation(() => {
      throw new Error('Storage error');
    });

    // Should not throw
    expect(() => clearConversation()).not.toThrow();
  });

  it('clearAllSessionData handles localStorage error gracefully', () => {
    vi.mocked(localStorage.removeItem).mockImplementation(() => {
      throw new Error('Storage error');
    });

    // Should not throw
    expect(() => clearAllSessionData()).not.toThrow();
  });
});

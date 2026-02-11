import { afterEach, vi } from 'vitest';

// Reset mocks after each test
afterEach(() => {
  vi.clearAllMocks();
  // Reset window.RevaConfig
  window.RevaConfig = undefined;
});

// Mock localStorage (happy-dom provides one, but we want to spy on it)
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      store = {};
    }),
    get length() {
      return Object.keys(store).length;
    },
    key: vi.fn((index: number) => Object.keys(store)[index] ?? null),
  };
})();

Object.defineProperty(globalThis, 'localStorage', {
  value: localStorageMock,
  writable: true,
});

// Mock crypto.randomUUID if not available
if (!globalThis.crypto?.randomUUID) {
  Object.defineProperty(globalThis, 'crypto', {
    value: {
      ...globalThis.crypto,
      randomUUID: vi.fn(() => 'mock-uuid-1234-5678-9abc-def012345678'),
    },
    writable: true,
  });
} else {
  // Spy on existing crypto.randomUUID
  vi.spyOn(globalThis.crypto, 'randomUUID').mockReturnValue(
    'mock-uuid-1234-5678-9abc-def012345678'
  );
}

// Extend window with RevaConfig (don't overwrite window)
declare global {
  interface Window {
    RevaConfig?: {
      storeId?: string;
      apiUrl?: string;
      position?: 'left' | 'right';
      theme?: { primaryColor?: string };
    };
  }
}

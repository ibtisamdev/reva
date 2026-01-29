/**
 * Conversations API functions
 */

import { apiGet, apiPatch } from './client';
import type {
  Conversation,
  ConversationDetail,
  ConversationStatus,
  PaginatedResponse,
} from './types';

// === Query Functions (for useQuery) ===

export async function getConversations(
  storeId: string,
  options?: {
    status?: ConversationStatus;
    search?: string;
    page?: number;
    pageSize?: number;
  }
): Promise<PaginatedResponse<Conversation>> {
  return apiGet<PaginatedResponse<Conversation>>('/api/v1/chat/conversations', {
    params: {
      store_id: storeId,
      status: options?.status,
      search: options?.search,
      page: options?.page || 1,
      page_size: options?.pageSize || 20,
    },
  });
}

export async function getConversation(
  conversationId: string,
  storeId: string
): Promise<ConversationDetail> {
  return apiGet<ConversationDetail>(`/api/v1/chat/conversations/${conversationId}`, {
    params: { store_id: storeId },
  });
}

// === Mutation Functions (for useMutation) ===

export async function updateConversationStatus(
  conversationId: string,
  storeId: string,
  status: ConversationStatus
): Promise<Conversation> {
  return apiPatch<Conversation>(`/api/v1/chat/conversations/${conversationId}/status`, {
    params: { store_id: storeId },
    body: { status },
  });
}

// === Query Keys ===

export const conversationKeys = {
  all: ['conversations'] as const,
  lists: () => [...conversationKeys.all, 'list'] as const,
  list: (storeId: string, filters?: { status?: ConversationStatus; search?: string }) =>
    [...conversationKeys.lists(), storeId, filters] as const,
  details: () => [...conversationKeys.all, 'detail'] as const,
  detail: (storeId: string, conversationId: string) =>
    [...conversationKeys.details(), storeId, conversationId] as const,
};

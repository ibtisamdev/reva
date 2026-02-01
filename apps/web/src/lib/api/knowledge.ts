/**
 * Knowledge Base API functions
 */

import { getAuthToken } from '@/lib/auth-client';

import { API_BASE_URL, apiDelete, apiGet, apiPatch, apiPost } from './client';
import type {
  ContentType,
  CreateKnowledgeFromUrlRequest,
  CreateKnowledgeRequest,
  IngestionResponse,
  KnowledgeArticle,
  KnowledgeArticleDetail,
  PaginatedResponse,
  UpdateKnowledgeRequest,
} from './types';

// === Query Functions (for useQuery) ===

export async function getKnowledgeArticles(
  storeId: string,
  options?: {
    contentType?: ContentType;
    page?: number;
    pageSize?: number;
  }
): Promise<PaginatedResponse<KnowledgeArticle>> {
  return apiGet<PaginatedResponse<KnowledgeArticle>>('/api/v1/knowledge', {
    params: {
      store_id: storeId,
      content_type: options?.contentType,
      page: options?.page || 1,
      page_size: options?.pageSize || 20,
    },
  });
}

export async function getKnowledgeArticle(
  articleId: string,
  storeId: string
): Promise<KnowledgeArticleDetail> {
  return apiGet<KnowledgeArticleDetail>(`/api/v1/knowledge/${articleId}`, {
    params: { store_id: storeId },
  });
}

// === Mutation Functions (for useMutation) ===

export async function createKnowledgeArticle(
  storeId: string,
  data: CreateKnowledgeRequest
): Promise<IngestionResponse> {
  return apiPost<IngestionResponse>('/api/v1/knowledge', {
    params: { store_id: storeId },
    body: data,
  });
}

export async function updateKnowledgeArticle(
  articleId: string,
  storeId: string,
  data: UpdateKnowledgeRequest
): Promise<KnowledgeArticle> {
  return apiPatch<KnowledgeArticle>(`/api/v1/knowledge/${articleId}`, {
    params: { store_id: storeId },
    body: data,
  });
}

export async function deleteKnowledgeArticle(
  articleId: string,
  storeId: string
): Promise<void> {
  return apiDelete(`/api/v1/knowledge/${articleId}`, {
    params: { store_id: storeId },
  });
}

export async function createKnowledgeFromUrl(
  storeId: string,
  data: CreateKnowledgeFromUrlRequest
): Promise<IngestionResponse> {
  return apiPost<IngestionResponse>('/api/v1/knowledge/url', {
    params: { store_id: storeId },
    body: data,
  });
}

export async function createKnowledgeFromPdf(
  storeId: string,
  formData: FormData
): Promise<IngestionResponse> {
  const url = new URL(`${API_BASE_URL}/api/v1/knowledge/pdf`);
  url.searchParams.append('store_id', storeId);

  const token = await getAuthToken();
  const headers: Record<string, string> = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(url.toString(), {
    method: 'POST',
    headers,
    body: formData,
    credentials: 'include',
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
    throw new Error(err.detail || `HTTP ${response.status}`);
  }

  return response.json() as Promise<IngestionResponse>;
}

// === Query Keys ===

export const knowledgeKeys = {
  all: ['knowledge'] as const,
  lists: () => [...knowledgeKeys.all, 'list'] as const,
  list: (storeId: string, filters?: { contentType?: ContentType }) =>
    [...knowledgeKeys.lists(), storeId, filters] as const,
  details: () => [...knowledgeKeys.all, 'detail'] as const,
  detail: (storeId: string, articleId: string) =>
    [...knowledgeKeys.details(), storeId, articleId] as const,
};

import http from './http'
import type {
  AskResponse,
  CancelQuestionResponse,
  ConversationDetail,
  ConversationSummary,
} from '../types'

export async function askQuestionApi(
  collectionId: string,
  question: string,
  conversationId?: number | null,
  requestId?: string,
  signal?: AbortSignal,
): Promise<AskResponse> {
  const { data } = await http.post<AskResponse>('/api/chat/ask', {
    collection_id: collectionId,
    question,
    conversation_id: conversationId || null,
    request_id: requestId || null,
  }, { signal })
  return data
}

export async function cancelQuestionApi(requestId: string): Promise<CancelQuestionResponse> {
  const { data } = await http.post<CancelQuestionResponse>(
    `/api/chat/requests/${encodeURIComponent(requestId)}/cancel`,
  )
  return data
}

export async function listConversationsApi(
  knowledgeBaseId?: number,
): Promise<ConversationSummary[]> {
  const { data } = await http.get<ConversationSummary[]>('/api/chat/conversations', {
    params: knowledgeBaseId ? { knowledge_base_id: knowledgeBaseId } : undefined,
  })
  return data
}

export async function getConversationApi(id: number): Promise<ConversationDetail> {
  const { data } = await http.get<ConversationDetail>(`/api/chat/conversations/${id}`)
  return data
}

export async function deleteConversationApi(id: number): Promise<void> {
  await http.delete(`/api/chat/conversations/${id}`)
}

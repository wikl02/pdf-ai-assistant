import http from './http'
import type { AskResponse } from '../types'

export async function askQuestionApi(
  collectionId: string,
  question: string,
): Promise<AskResponse> {
  // collection_id 限定检索范围，防止不同知识库的内容混入同一次回答。
  const { data } = await http.post<AskResponse>('/api/chat/ask', {
    collection_id: collectionId,
    question,
  })
  return data
}

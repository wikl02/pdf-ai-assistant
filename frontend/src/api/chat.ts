import http from './http'
import type { AskResponse } from '../types'

export async function askQuestionApi(
  collectionId: string,
  question: string,
): Promise<AskResponse> {
  const { data } = await http.post<AskResponse>('/api/chat/ask', {
    collection_id: collectionId,
    question,
  })
  return data
}

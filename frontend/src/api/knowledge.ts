import http from './http'
import type {
  DocumentUploadResponse,
  KnowledgeBase,
  KnowledgeBaseDetail,
  KnowledgeDocument,
} from '../types'

export async function listAdminKnowledgeBasesApi(): Promise<KnowledgeBase[]> {
  const { data } = await http.get<KnowledgeBase[]>('/api/admin/knowledge-bases')
  return data
}

export async function listAccessibleKnowledgeBasesApi(): Promise<KnowledgeBase[]> {
  const { data } = await http.get<KnowledgeBase[]>('/api/knowledge-bases')
  return data
}

export async function createKnowledgeBaseApi(payload: {
  name: string
  description?: string
}): Promise<KnowledgeBase> {
  const { data } = await http.post<KnowledgeBase>('/api/admin/knowledge-bases', payload)
  return data
}

export async function getKnowledgeBaseApi(id: number): Promise<KnowledgeBaseDetail> {
  const { data } = await http.get<KnowledgeBaseDetail>(`/api/admin/knowledge-bases/${id}`)
  return data
}

export async function uploadDocumentsApi(
  knowledgeBaseId: number,
  files: File[],
): Promise<DocumentUploadResponse> {
  const form = new FormData()
  files.forEach((file) => form.append('files', file))
  const { data } = await http.post<DocumentUploadResponse>(
    `/api/admin/knowledge-bases/${knowledgeBaseId}/documents`,
    form,
  )
  return data
}

export async function deleteDocumentApi(
  knowledgeBaseId: number,
  documentId: number,
): Promise<void> {
  await http.delete(`/api/admin/knowledge-bases/${knowledgeBaseId}/documents/${documentId}`)
}

export async function reindexDocumentApi(
  knowledgeBaseId: number,
  documentId: number,
): Promise<KnowledgeDocument> {
  const { data } = await http.post<KnowledgeDocument>(
    `/api/admin/knowledge-bases/${knowledgeBaseId}/documents/${documentId}/reindex`,
  )
  return data
}

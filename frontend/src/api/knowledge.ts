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
  // 后端参数名是 files；多次 append 可在一个 multipart 请求中上传多个文档。
  files.forEach((file) => form.append('files', file))
  const { data } = await http.post<DocumentUploadResponse>(
    `/api/admin/knowledge-bases/${knowledgeBaseId}/documents`,
    form,
    // 上传后还会同步解析、计算 Embedding 和写入 Chroma，单独放宽到 15 分钟。
    { timeout: 900_000 },
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

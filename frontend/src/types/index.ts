export type UserRole = 'admin' | 'user'
export type DocumentStatus = 'pending' | 'processing' | 'ready' | 'failed'

export interface User {
  id: number
  username: string
  display_name: string | null
  role: UserRole
  is_active: boolean
  created_at: string
  updated_at: string
  last_login_at: string | null
}

export interface LoginResponse {
  access_token: string
  token_type: string
  expires_in: number
  user: User
}

export interface KnowledgeBase {
  id: number
  name: string
  description: string | null
  collection_name: string
  created_by_id: number
  document_count: number
  chunk_count: number
  created_at: string
  updated_at: string
}

export interface KnowledgeDocument {
  id: number
  filename: string
  file_type: string
  file_size: number
  sha256: string
  storage_path: string
  status: DocumentStatus
  chunk_count: number
  error_message: string | null
  uploaded_by_id: number
  created_at: string
  updated_at: string
}

export interface KnowledgeBaseDetail extends KnowledgeBase {
  documents: KnowledgeDocument[]
}

export interface DocumentUploadResponse {
  knowledge_base_id: number
  collection_id: string
  documents: KnowledgeDocument[]
  document_count: number
  chunk_count: number
}

export interface SourceMetadata {
  source_name?: string
  file_type?: string
  location_type?: string
  page?: number
  start_line?: number
  end_line?: number
  sheet?: string
  chunk_id?: number
  document_id?: string
}

export interface SourceChunk {
  text: string
  metadata: SourceMetadata
  score: number
}

export interface AskResponse {
  answer: string
  sources: SourceChunk[]
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: SourceChunk[]
  status?: 'loading' | 'error' | 'done'
}

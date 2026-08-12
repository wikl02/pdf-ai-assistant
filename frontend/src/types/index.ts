export type UserRole = 'super_admin' | 'admin' | 'user'
export type DocumentStatus = 'pending' | 'processing' | 'ready' | 'failed'
export type IndexTaskStatus = 'pending' | 'processing' | 'succeeded' | 'failed'
export type IndexTaskTrigger = 'upload' | 'version_upload' | 'reindex'
export type EvaluationRunStatus = 'running' | 'completed' | 'failed'
export type ReviewStatus = 'unreviewed' | 'passed' | 'failed'

export interface User {
  id: number
  username: string
  display_name: string | null
  role: UserRole
  is_active: boolean
  created_at: string
  updated_at: string
  last_login_at: string | null
  deleted_at: string | null
  deleted_by_id: number | null
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
  current_version_number: number
  uploaded_by_id: number
  created_at: string
  updated_at: string
}

export interface DocumentVersion {
  id: number
  document_id: number
  version_number: number
  filename: string
  file_type: string
  file_size: number
  sha256: string
  status: DocumentStatus
  chunk_count: number
  error_message: string | null
  created_by_id: number | null
  created_at: string
}

export interface DocumentIndexTask {
  id: number
  document_id: number
  knowledge_base_id: number
  version_number: number
  trigger: IndexTaskTrigger
  status: IndexTaskStatus
  chunk_count: number
  error_message: string | null
  duration_ms: number | null
  initiated_by_id: number | null
  started_at: string | null
  completed_at: string | null
  created_at: string
}

export interface DocumentLifecycle {
  document: KnowledgeDocument
  versions: DocumentVersion[]
  index_tasks: DocumentIndexTask[]
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
  conversation_id: number | null
  user_message_id: number | null
  assistant_message_id: number | null
}

export interface ChatMessage {
  id: string | number
  role: 'user' | 'assistant'
  content: string
  sources?: SourceChunk[]
  status?: 'loading' | 'error' | 'done'
  response_time_ms?: number | null
  created_at?: string
}

export interface ConversationSummary {
  id: number
  user_id: number
  knowledge_base_id: number
  knowledge_base_name: string
  title: string
  message_count: number
  created_at: string
  updated_at: string
}

export interface ConversationDetail extends ConversationSummary {
  messages: Array<{
    id: number
    conversation_id: number
    role: 'user' | 'assistant'
    content: string
    sources: SourceChunk[] | null
    status: 'complete' | 'failed'
    response_time_ms: number | null
    created_at: string
  }>
}

export interface AuditLog {
  id: number
  event: string
  outcome: 'success' | 'failed'
  actor_id: number | null
  actor_name: string | null
  client_ip: string | null
  details: Record<string, unknown> | null
  created_at: string
}

export interface AuditLogList {
  items: AuditLog[]
  total: number
  page: number
  page_size: number
}

export interface UsageSummary {
  audit_event_count: number
  question_count: number
  failed_event_count: number
  active_user_count: number
  conversation_count: number
  message_count: number
}

export interface EvaluationSummary {
  dataset_count: number
  case_count: number
  completed_run_count: number
  latest_answer_hit_rate: number | null
  latest_source_hit_rate: number | null
  latest_average_response_time_ms: number | null
}

export interface EvaluationDataset {
  id: number
  name: string
  description: string | null
  knowledge_base_id: number
  knowledge_base_name: string
  is_active: boolean
  created_by_id: number | null
  case_count: number
  run_count: number
  created_at: string
  updated_at: string
}

export interface EvaluationCasePayload {
  question: string
  expected_answer_keywords: string[]
  expected_source_names: string[]
  notes?: string | null
  is_active: boolean
}

export interface EvaluationCase extends EvaluationCasePayload {
  id: number
  dataset_id: number
  notes: string | null
  created_at: string
  updated_at: string
}

export interface EvaluationResult {
  id: number
  run_id: number
  case_id: number | null
  question: string
  expected_answer_keywords: string[]
  expected_source_names: string[]
  answer: string | null
  sources: SourceChunk[]
  answer_keyword_hits: string[]
  source_hits: string[]
  answer_hit: boolean
  source_hit: boolean
  response_time_ms: number | null
  error_message: string | null
  review_status: ReviewStatus
  reviewer_id: number | null
  review_note: string | null
  reviewed_at: string | null
  created_at: string
}

export interface EvaluationRun {
  id: number
  dataset_id: number
  status: EvaluationRunStatus
  total_cases: number
  completed_cases: number
  answer_hit_count: number
  source_hit_count: number
  average_response_time_ms: number | null
  error_message: string | null
  triggered_by_id: number | null
  started_at: string
  completed_at: string | null
  created_at: string
  results: EvaluationResult[]
}

export interface EvaluationDatasetDetail extends EvaluationDataset {
  cases: EvaluationCase[]
  recent_runs: Omit<EvaluationRun, 'results'>[]
}

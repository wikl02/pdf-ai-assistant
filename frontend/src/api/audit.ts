import http from './http'
import type { AuditLogList, UsageSummary } from '../types'

export interface AuditLogFilters {
  event?: string
  outcome?: string
  actor_id?: number
  page?: number
  page_size?: number
}

export async function listAuditLogsApi(filters: AuditLogFilters): Promise<AuditLogList> {
  const { data } = await http.get<AuditLogList>('/api/admin/audit-logs', {
    params: filters,
  })
  return data
}

export async function getUsageSummaryApi(): Promise<UsageSummary> {
  const { data } = await http.get<UsageSummary>('/api/admin/audit-logs/summary')
  return {
    ...data,
    prompt_tokens: data.prompt_tokens ?? 0,
    completion_tokens: data.completion_tokens ?? 0,
    total_tokens: data.total_tokens ?? 0,
  }
}

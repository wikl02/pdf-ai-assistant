import http from './http'
import type {
  EvaluationCase,
  EvaluationCasePayload,
  EvaluationDataset,
  EvaluationDatasetDetail,
  EvaluationRun,
  EvaluationSummary,
  ReviewStatus,
} from '../types'

export async function getEvaluationSummaryApi(): Promise<EvaluationSummary> {
  const { data } = await http.get<EvaluationSummary>('/api/admin/evaluations/summary')
  return data
}

export async function listEvaluationDatasetsApi(): Promise<EvaluationDataset[]> {
  const { data } = await http.get<EvaluationDataset[]>('/api/admin/evaluations/datasets')
  return data
}

export async function createEvaluationDatasetApi(payload: {
  name: string
  description?: string
  knowledge_base_id: number
}): Promise<EvaluationDataset> {
  const { data } = await http.post<EvaluationDataset>('/api/admin/evaluations/datasets', payload)
  return data
}

export async function deleteEvaluationDatasetApi(datasetId: number): Promise<void> {
  await http.delete(`/api/admin/evaluations/datasets/${datasetId}`)
}

export async function getEvaluationDatasetApi(datasetId: number): Promise<EvaluationDatasetDetail> {
  const { data } = await http.get<EvaluationDatasetDetail>(
    `/api/admin/evaluations/datasets/${datasetId}`,
  )
  return data
}

export async function createEvaluationCaseApi(
  datasetId: number,
  payload: EvaluationCasePayload,
): Promise<EvaluationCase> {
  const { data } = await http.post<EvaluationCase>(
    `/api/admin/evaluations/datasets/${datasetId}/cases`,
    payload,
  )
  return data
}

export async function updateEvaluationCaseApi(
  datasetId: number,
  caseId: number,
  payload: EvaluationCasePayload,
): Promise<EvaluationCase> {
  const { data } = await http.patch<EvaluationCase>(
    `/api/admin/evaluations/datasets/${datasetId}/cases/${caseId}`,
    payload,
  )
  return data
}

export async function deleteEvaluationCaseApi(datasetId: number, caseId: number): Promise<void> {
  await http.delete(`/api/admin/evaluations/datasets/${datasetId}/cases/${caseId}`)
}

export async function runEvaluationApi(datasetId: number): Promise<EvaluationRun> {
  const { data } = await http.post<EvaluationRun>(
    `/api/admin/evaluations/datasets/${datasetId}/runs`,
    undefined,
    { timeout: 900_000 },
  )
  return data
}

export async function getEvaluationRunApi(runId: number): Promise<EvaluationRun> {
  const { data } = await http.get<EvaluationRun>(`/api/admin/evaluations/runs/${runId}`)
  return data
}

export async function reviewEvaluationResultApi(
  runId: number,
  resultId: number,
  payload: { review_status: ReviewStatus; review_note?: string },
): Promise<void> {
  await http.patch(
    `/api/admin/evaluations/runs/${runId}/results/${resultId}/review`,
    payload,
  )
}

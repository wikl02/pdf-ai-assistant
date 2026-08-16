<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  CheckCircle2,
  ClipboardCheck,
  FileSearch,
  Gauge,
  Play,
  Plus,
  RefreshCw,
  Trash2,
} from '@lucide/vue'

import {
  createEvaluationCaseApi,
  createEvaluationDatasetApi,
  deleteEvaluationCaseApi,
  deleteEvaluationDatasetApi,
  getEvaluationDatasetApi,
  getEvaluationRunApi,
  getEvaluationSummaryApi,
  listEvaluationDatasetsApi,
  reviewEvaluationResultApi,
  runEvaluationApi,
  updateEvaluationCaseApi,
} from '../../api/evaluations'
import { getErrorMessage } from '../../api/http'
import { listAdminKnowledgeBasesApi } from '../../api/knowledge'
import PageHeader from '../../components/common/PageHeader.vue'
import type {
  EvaluationCase,
  EvaluationCasePayload,
  EvaluationDataset,
  EvaluationDatasetDetail,
  EvaluationResult,
  EvaluationRun,
  EvaluationSummary,
  KnowledgeBase,
  ReviewStatus,
} from '../../types'

const loading = ref(true)
const detailLoading = ref(false)
const running = ref(false)
const errorMessage = ref('')
const datasets = ref<EvaluationDataset[]>([])
const knowledgeBases = ref<KnowledgeBase[]>([])
const selectedDatasetId = ref<number | null>(null)
const detail = ref<EvaluationDatasetDetail | null>(null)
const runDetail = ref<EvaluationRun | null>(null)
const runDrawerOpen = ref(false)
const runLoading = ref(false)
const datasetDialogOpen = ref(false)
const caseDialogOpen = ref(false)
const reviewDialogOpen = ref(false)
const editingCaseId = ref<number | null>(null)
const reviewingResult = ref<EvaluationResult | null>(null)
const summary = ref<EvaluationSummary>({
  dataset_count: 0,
  case_count: 0,
  completed_run_count: 0,
  latest_answer_hit_rate: null,
  latest_source_hit_rate: null,
  latest_average_response_time_ms: null,
})

const datasetForm = reactive({ name: '', description: '', knowledge_base_id: null as number | null })
const caseForm = reactive({
  question: '',
  answerKeywords: '',
  sourceNames: '',
  notes: '',
  is_active: true,
})
const reviewForm = reactive({ review_status: 'passed' as ReviewStatus, review_note: '' })

const metrics = computed(() => [
  { label: '问题集', value: summary.value.dataset_count, icon: ClipboardCheck, tone: 'blue' },
  { label: '标准问题', value: summary.value.case_count, icon: FileSearch, tone: 'green' },
  { label: '已完成运行', value: summary.value.completed_run_count, icon: Play, tone: 'gray' },
  {
    label: '最近回答命中',
    value: summary.value.latest_answer_hit_rate === null ? '-' : `${summary.value.latest_answer_hit_rate}%`,
    icon: Gauge,
    tone: 'amber',
  },
])

function splitValues(value: string) {
  return [...new Set(value.split(/[,，\n]/).map((item) => item.trim()).filter(Boolean))]
}

function formatDate(value: string | null) {
  return value ? new Date(value).toLocaleString('zh-CN') : '-'
}

function hitRate(hit: number, total: number) {
  return total ? `${Math.round((hit / total) * 100)}%` : '-'
}

function sourceNames(result: EvaluationResult) {
  const names = result.sources
    .map((item) => item.metadata?.source_name)
    .filter((item): item is string => Boolean(item))
  return names.length ? [...new Set(names)].join('、') : '无引用来源'
}

async function loadOverview(preferredId?: number) {
  loading.value = true
  errorMessage.value = ''
  try {
    const [datasetItems, summaryData, kbItems] = await Promise.all([
      listEvaluationDatasetsApi(),
      getEvaluationSummaryApi(),
      listAdminKnowledgeBasesApi(),
    ])
    datasets.value = datasetItems
    summary.value = summaryData
    knowledgeBases.value = kbItems
    const nextId = preferredId ?? selectedDatasetId.value ?? datasetItems[0]?.id ?? null
    selectedDatasetId.value = datasetItems.some((item) => item.id === nextId) ? nextId : null
    if (selectedDatasetId.value) await loadDetail(selectedDatasetId.value)
    else detail.value = null
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '质量评估数据加载失败')
  } finally {
    loading.value = false
  }
}

async function loadDetail(datasetId: number) {
  detailLoading.value = true
  selectedDatasetId.value = datasetId
  try {
    detail.value = await getEvaluationDatasetApi(datasetId)
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '问题集详情加载失败'))
  } finally {
    detailLoading.value = false
  }
}

function openDatasetDialog() {
  datasetForm.name = ''
  datasetForm.description = ''
  datasetForm.knowledge_base_id = knowledgeBases.value[0]?.id ?? null
  datasetDialogOpen.value = true
}

async function submitDataset() {
  if (!datasetForm.name.trim() || !datasetForm.knowledge_base_id) {
    ElMessage.warning('请填写问题集名称并选择知识库')
    return
  }
  try {
    const created = await createEvaluationDatasetApi({
      name: datasetForm.name.trim(),
      description: datasetForm.description.trim() || undefined,
      knowledge_base_id: datasetForm.knowledge_base_id,
    })
    datasetDialogOpen.value = false
    ElMessage.success('问题集已创建')
    await loadOverview(created.id)
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '问题集创建失败'))
  }
}

async function removeDataset() {
  if (!detail.value) return
  await ElMessageBox.confirm(
    `将删除“${detail.value.name}”及全部历史评估结果，此操作不可恢复。`,
    '删除问题集',
    { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
  )
  try {
    await deleteEvaluationDatasetApi(detail.value.id)
    selectedDatasetId.value = null
    ElMessage.success('问题集已删除')
    await loadOverview()
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '问题集删除失败'))
  }
}

function openCaseDialog(item?: EvaluationCase) {
  editingCaseId.value = item?.id ?? null
  caseForm.question = item?.question ?? ''
  caseForm.answerKeywords = item?.expected_answer_keywords.join('，') ?? ''
  caseForm.sourceNames = item?.expected_source_names.join('，') ?? ''
  caseForm.notes = item?.notes ?? ''
  caseForm.is_active = item?.is_active ?? true
  caseDialogOpen.value = true
}

async function submitCase() {
  if (!detail.value) return
  const payload: EvaluationCasePayload = {
    question: caseForm.question.trim(),
    expected_answer_keywords: splitValues(caseForm.answerKeywords),
    expected_source_names: splitValues(caseForm.sourceNames),
    notes: caseForm.notes.trim() || undefined,
    is_active: caseForm.is_active,
  }
  if (!payload.question || !payload.expected_answer_keywords.length || !payload.expected_source_names.length) {
    ElMessage.warning('问题、期望关键词和期望来源均不能为空')
    return
  }
  try {
    if (editingCaseId.value) {
      await updateEvaluationCaseApi(detail.value.id, editingCaseId.value, payload)
      ElMessage.success('标准问题已更新')
    } else {
      await createEvaluationCaseApi(detail.value.id, payload)
      ElMessage.success('标准问题已添加')
    }
    caseDialogOpen.value = false
    await loadOverview(detail.value.id)
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '标准问题保存失败'))
  }
}

async function removeCase(item: EvaluationCase) {
  if (!detail.value) return
  await ElMessageBox.confirm('删除后不会影响已有运行快照，但该问题将不再参与后续评估。', '删除标准问题', {
    type: 'warning',
    confirmButtonText: '删除',
    cancelButtonText: '取消',
  })
  try {
    await deleteEvaluationCaseApi(detail.value.id, item.id)
    ElMessage.success('标准问题已删除')
    await loadOverview(detail.value.id)
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '标准问题删除失败'))
  }
}

async function executeRun() {
  if (!detail.value) return
  const activeCount = detail.value.cases.filter((item) => item.is_active).length
  if (!activeCount) {
    ElMessage.warning('当前没有启用的标准问题')
    return
  }
  await ElMessageBox.confirm(
    `将依次执行 ${activeCount} 道问题，并调用当前检索与 AI 服务，可能产生 API 费用。`,
    '运行质量评估',
    { type: 'warning', confirmButtonText: '开始运行', cancelButtonText: '取消' },
  )
  running.value = true
  try {
    runDetail.value = await runEvaluationApi(detail.value.id)
    runDrawerOpen.value = true
    ElMessage.success('质量评估已完成')
    await loadOverview(detail.value.id)
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '质量评估执行失败'))
  } finally {
    running.value = false
  }
}

async function openRun(runId: number) {
  runDrawerOpen.value = true
  runLoading.value = true
  try {
    runDetail.value = await getEvaluationRunApi(runId)
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '评估结果加载失败'))
  } finally {
    runLoading.value = false
  }
}

function openReview(item: EvaluationResult) {
  reviewingResult.value = item
  reviewForm.review_status = item.review_status === 'unreviewed' ? 'passed' : item.review_status
  reviewForm.review_note = item.review_note ?? ''
  reviewDialogOpen.value = true
}

async function submitReview() {
  if (!runDetail.value || !reviewingResult.value) return
  try {
    await reviewEvaluationResultApi(runDetail.value.id, reviewingResult.value.id, {
      review_status: reviewForm.review_status,
      review_note: reviewForm.review_note.trim() || undefined,
    })
    reviewDialogOpen.value = false
    runDetail.value = await getEvaluationRunApi(runDetail.value.id)
    ElMessage.success('人工验收结果已保存')
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '验收结果保存失败'))
  }
}

onMounted(() => loadOverview())
</script>

<template>
  <section>
    <PageHeader title="问答质量评估" description="用标准问题集重复验证回答内容、引用来源和响应时间。">
      <template #actions>
        <el-button :loading="loading" @click="loadOverview()"><RefreshCw :size="16" />刷新</el-button>
        <el-button type="primary" @click="openDatasetDialog"><Plus :size="16" />创建问题集</el-button>
      </template>
    </PageHeader>

    <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon @close="errorMessage = ''" />

    <div class="metric-grid evaluation-metrics">
      <article v-for="metric in metrics" :key="metric.label" class="metric-card">
        <span :class="['metric-icon', metric.tone]"><component :is="metric.icon" :size="21" /></span>
        <div><span>{{ metric.label }}</span><strong>{{ metric.value }}</strong></div>
      </article>
    </div>

    <div v-loading="loading" class="evaluation-workspace">
      <aside class="evaluation-datasets">
        <div class="evaluation-panel-heading">
          <div><strong>标准问题集</strong><span>{{ datasets.length }} 个</span></div>
        </div>
        <button
          v-for="item in datasets"
          :key="item.id"
          :class="['evaluation-dataset-item', { active: item.id === selectedDatasetId }]"
          @click="loadDetail(item.id)"
        >
          <ClipboardCheck :size="18" />
          <span><strong>{{ item.name }}</strong><small>{{ item.knowledge_base_name }} · {{ item.case_count }} 题</small></span>
        </button>
        <div v-if="!datasets.length && !loading" class="evaluation-empty">尚未创建标准问题集</div>
      </aside>

      <main v-loading="detailLoading" class="evaluation-detail">
        <template v-if="detail">
          <header class="evaluation-detail-header">
            <div>
              <h2>{{ detail.name }}</h2>
              <p>{{ detail.description || '暂无说明' }}</p>
              <span>关联知识库：{{ detail.knowledge_base_name }}</span>
            </div>
            <div class="evaluation-detail-actions">
              <el-button type="danger" plain @click="removeDataset"><Trash2 :size="15" />删除</el-button>
              <el-button @click="openCaseDialog()"><Plus :size="15" />添加问题</el-button>
              <el-button type="primary" :loading="running" @click="executeRun"><Play :size="15" />运行评估</el-button>
            </div>
          </header>

          <section class="evaluation-table-section">
            <div class="section-heading compact"><div><h2>标准问题</h2><p>启用的问题会进入下一次评估。</p></div></div>
            <el-table :data="detail.cases" size="small" empty-text="暂无标准问题">
              <el-table-column label="问题" min-width="250">
                <template #default="scope"><div class="primary-cell"><strong>{{ scope.row.question }}</strong><span>{{ scope.row.notes || '-' }}</span></div></template>
              </el-table-column>
              <el-table-column label="期望关键词" min-width="180">
                <template #default="scope"><el-tag v-for="item in scope.row.expected_answer_keywords" :key="item" size="small" class="evaluation-tag">{{ item }}</el-tag></template>
              </el-table-column>
              <el-table-column label="期望来源" min-width="170" show-overflow-tooltip>
                <template #default="scope">{{ scope.row.expected_source_names.join('、') }}</template>
              </el-table-column>
              <el-table-column label="状态" width="90">
                <template #default="scope"><el-tag :type="scope.row.is_active ? 'success' : 'info'" size="small">{{ scope.row.is_active ? '启用' : '停用' }}</el-tag></template>
              </el-table-column>
              <el-table-column label="操作" width="130" fixed="right">
                <template #default="scope"><el-button link type="primary" @click="openCaseDialog(scope.row)">编辑</el-button><el-button link type="danger" @click="removeCase(scope.row)">删除</el-button></template>
              </el-table-column>
            </el-table>
          </section>

          <section class="evaluation-table-section run-history-section">
            <div class="section-heading compact"><div><h2>最近运行</h2><p>保存每次执行的自动指标和人工验收结果。</p></div></div>
            <el-table :data="detail.recent_runs" size="small" empty-text="尚未运行评估">
              <el-table-column label="运行时间" min-width="180"><template #default="scope">{{ formatDate(scope.row.started_at) }}</template></el-table-column>
              <el-table-column label="回答命中" width="110"><template #default="scope">{{ hitRate(scope.row.answer_hit_count, scope.row.total_cases) }}</template></el-table-column>
              <el-table-column label="来源命中" width="110"><template #default="scope">{{ hitRate(scope.row.source_hit_count, scope.row.total_cases) }}</template></el-table-column>
              <el-table-column label="平均耗时" width="120"><template #default="scope">{{ scope.row.average_response_time_ms === null ? '-' : `${Math.round(scope.row.average_response_time_ms)} ms` }}</template></el-table-column>
              <el-table-column label="执行情况" width="120"><template #default="scope"><el-tag :type="scope.row.error_message ? 'warning' : 'success'" size="small">{{ scope.row.error_message || `${scope.row.completed_cases}/${scope.row.total_cases} 完成` }}</el-tag></template></el-table-column>
              <el-table-column label="操作" width="90"><template #default="scope"><el-button link type="primary" @click="openRun(scope.row.id)">查看结果</el-button></template></el-table-column>
            </el-table>
          </section>
        </template>
        <div v-else class="evaluation-empty detail-empty"><ClipboardCheck :size="34" /><strong>选择或创建问题集</strong><span>标准问题将绑定一个知识库执行回归评估。</span></div>
      </main>
    </div>

    <el-dialog v-model="datasetDialogOpen" title="创建标准问题集" width="520px" class="responsive-dialog">
      <el-form label-position="top">
        <el-form-item label="问题集名称" required><el-input v-model="datasetForm.name" maxlength="160" /></el-form-item>
        <el-form-item label="关联知识库" required><el-select v-model="datasetForm.knowledge_base_id" placeholder="选择知识库"><el-option v-for="item in knowledgeBases" :key="item.id" :label="item.name" :value="item.id" /></el-select></el-form-item>
        <el-form-item label="说明"><el-input v-model="datasetForm.description" type="textarea" :rows="3" maxlength="2000" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="datasetDialogOpen = false">取消</el-button><el-button type="primary" @click="submitDataset">创建</el-button></template>
    </el-dialog>

    <el-dialog v-model="caseDialogOpen" :title="editingCaseId ? '编辑标准问题' : '添加标准问题'" width="620px" class="responsive-dialog">
      <el-form label-position="top">
        <el-form-item label="问题" required><el-input v-model="caseForm.question" type="textarea" :rows="3" maxlength="5000" /></el-form-item>
        <el-form-item label="期望回答关键词" required><el-input v-model="caseForm.answerKeywords" placeholder="多个关键词用逗号分隔，例如：7天，退款" /><small class="form-hint">回答必须包含全部关键词才算自动命中。</small></el-form-item>
        <el-form-item label="期望来源文档" required><el-input v-model="caseForm.sourceNames" placeholder="多个文件名用逗号分隔，例如：产品FAQ.txt" /><small class="form-hint">引用任意一个期望来源即算来源命中。</small></el-form-item>
        <el-form-item label="验收备注"><el-input v-model="caseForm.notes" type="textarea" :rows="2" maxlength="2000" /></el-form-item>
        <el-form-item label="参与评估"><el-switch v-model="caseForm.is_active" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="caseDialogOpen = false">取消</el-button><el-button type="primary" @click="submitCase">保存</el-button></template>
    </el-dialog>

    <el-drawer v-model="runDrawerOpen" title="评估运行结果" size="min(920px, 92vw)" class="evaluation-drawer">
      <div v-loading="runLoading" class="run-detail-content">
        <template v-if="runDetail">
          <div class="run-summary-strip">
            <div><span>回答命中</span><strong>{{ hitRate(runDetail.answer_hit_count, runDetail.total_cases) }}</strong></div>
            <div><span>来源命中</span><strong>{{ hitRate(runDetail.source_hit_count, runDetail.total_cases) }}</strong></div>
            <div><span>平均耗时</span><strong>{{ Math.round(runDetail.average_response_time_ms || 0) }} ms</strong></div>
            <div><span>运行时间</span><strong>{{ formatDate(runDetail.started_at) }}</strong></div>
          </div>
          <el-alert v-if="runDetail.error_message" :title="runDetail.error_message" type="warning" show-icon :closable="false" />
          <el-table :data="runDetail.results" size="small" empty-text="暂无结果">
            <el-table-column type="expand">
              <template #default="scope">
                <div class="evaluation-result-detail">
                  <div><span>AI 回答</span><p>{{ scope.row.answer || scope.row.error_message || '没有生成回答' }}</p></div>
                  <div><span>引用来源</span><p>{{ sourceNames(scope.row) }}</p></div>
                  <div><span>关键词命中</span><p>{{ scope.row.answer_keyword_hits.join('、') || '无' }}</p></div>
                  <div v-if="scope.row.review_note"><span>人工备注</span><p>{{ scope.row.review_note }}</p></div>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="问题" min-width="260" show-overflow-tooltip prop="question" />
            <el-table-column label="回答" width="90"><template #default="scope"><el-tag :type="scope.row.answer_hit ? 'success' : 'danger'" size="small">{{ scope.row.answer_hit ? '命中' : '未命中' }}</el-tag></template></el-table-column>
            <el-table-column label="来源" width="90"><template #default="scope"><el-tag :type="scope.row.source_hit ? 'success' : 'danger'" size="small">{{ scope.row.source_hit ? '命中' : '未命中' }}</el-tag></template></el-table-column>
            <el-table-column label="耗时" width="90"><template #default="scope">{{ scope.row.response_time_ms }} ms</template></el-table-column>
            <el-table-column label="Token" width="90"><template #default="scope">{{ scope.row.total_tokens ?? '-' }}</template></el-table-column>
            <el-table-column label="人工验收" width="100"><template #default="scope"><el-tag :type="scope.row.review_status === 'passed' ? 'success' : scope.row.review_status === 'failed' ? 'danger' : 'info'" size="small">{{ scope.row.review_status === 'passed' ? '通过' : scope.row.review_status === 'failed' ? '不通过' : '未验收' }}</el-tag></template></el-table-column>
            <el-table-column label="操作" width="80"><template #default="scope"><el-button link type="primary" @click="openReview(scope.row)">验收</el-button></template></el-table-column>
          </el-table>
        </template>
      </div>
    </el-drawer>

    <el-dialog v-model="reviewDialogOpen" title="人工验收" width="500px" class="responsive-dialog">
      <el-form label-position="top">
        <el-form-item label="验收结论"><el-radio-group v-model="reviewForm.review_status"><el-radio-button value="passed"><CheckCircle2 :size="15" />通过</el-radio-button><el-radio-button value="failed">不通过</el-radio-button></el-radio-group></el-form-item>
        <el-form-item label="验收备注"><el-input v-model="reviewForm.review_note" type="textarea" :rows="4" maxlength="2000" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="reviewDialogOpen = false">取消</el-button><el-button type="primary" @click="submitReview">保存验收</el-button></template>
    </el-dialog>
  </section>
</template>

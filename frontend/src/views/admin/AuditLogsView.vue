<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { Activity, AlertTriangle, Coins, MessageSquareText, RefreshCw, Users } from '@lucide/vue'

import { getUsageSummaryApi, listAuditLogsApi } from '../../api/audit'
import { getErrorMessage } from '../../api/http'
import PageHeader from '../../components/common/PageHeader.vue'
import type { AuditLog, UsageSummary } from '../../types'

const loading = ref(true)
const errorMessage = ref('')
const logs = ref<AuditLog[]>([])
const total = ref(0)
const summary = ref<UsageSummary>({
  audit_event_count: 0,
  question_count: 0,
  failed_event_count: 0,
  active_user_count: 0,
  conversation_count: 0,
  message_count: 0,
  prompt_tokens: 0,
  completion_tokens: 0,
  total_tokens: 0,
})
const filters = reactive({ event: '', outcome: '', page: 1, page_size: 30 })

const metrics = computed(() => [
  { label: '审计事件', value: summary.value.audit_event_count, icon: Activity, tone: 'blue' },
  { label: '成功问答', value: summary.value.question_count, icon: MessageSquareText, tone: 'green' },
  { label: '失败事件', value: summary.value.failed_event_count, icon: AlertTriangle, tone: 'amber' },
  { label: '活跃用户', value: summary.value.active_user_count, icon: Users, tone: 'gray' },
  { label: '累计 Token', value: summary.value.total_tokens, icon: Coins, tone: 'blue' },
])

const eventOptions: Array<[string, string]> = [
  ['login', '用户登录'],
  ['question_answered', '知识问答'],
  ['documents_uploaded', '上传文档'],
  ['document_deleted', '删除文档'],
  ['document_reindexed', '重建索引'],
  ['knowledge_base_permission_granted', '知识库授权'],
  ['knowledge_base_permission_revoked', '撤销授权'],
  ['user_created', '创建用户'],
  ['user_status_changed', '修改用户状态'],
  ['user_deleted', '删除用户'],
  ['user_restored', '恢复用户'],
  ['document_version_uploaded', '上传文档版本'],
  ['evaluation_dataset_created', '创建评估问题集'],
  ['evaluation_dataset_updated', '修改评估问题集'],
  ['evaluation_dataset_deleted', '删除评估问题集'],
  ['evaluation_case_created', '添加标准问题'],
  ['evaluation_case_updated', '修改标准问题'],
  ['evaluation_case_deleted', '删除标准问题'],
  ['evaluation_run_completed', '运行质量评估'],
  ['evaluation_result_reviewed', '人工验收结果'],
  ['conversation_deleted', '删除会话'],
]
const eventLabels: Record<string, string> = Object.fromEntries(eventOptions)

async function loadData() {
  loading.value = true
  errorMessage.value = ''
  try {
    const [list, usage] = await Promise.all([
      listAuditLogsApi({
        event: filters.event || undefined,
        outcome: filters.outcome || undefined,
        page: filters.page,
        page_size: filters.page_size,
      }),
      getUsageSummaryApi(),
    ])
    logs.value = list.items
    total.value = list.total
    summary.value = usage
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '审计数据加载失败')
  } finally {
    loading.value = false
  }
}

function applyFilters() {
  filters.page = 1
  loadData()
}

function resetFilters() {
  filters.event = ''
  filters.outcome = ''
  filters.page = 1
  loadData()
}

function formatDetails(details: Record<string, unknown> | null) {
  if (!details || !Object.keys(details).length) return '-'
  if ('total_tokens' in details) {
    const model = details.llm_model ? `模型: ${String(details.llm_model)}` : '未调用模型'
    return [
      model,
      `输入 Token: ${String(details.prompt_tokens ?? '-')}`,
      `输出 Token: ${String(details.completion_tokens ?? '-')}`,
      `总 Token: ${String(details.total_tokens ?? '-')}`,
    ].join(' · ')
  }
  return Object.entries(details)
    .slice(0, 4)
    .map(([key, value]) => `${key}: ${String(value)}`)
    .join(' · ')
}

onMounted(loadData)
</script>

<template>
  <section>
    <PageHeader title="审计日志" description="查询关键操作记录和系统使用概况。">
      <template #actions>
        <el-button :loading="loading" @click="loadData">
          <RefreshCw :size="16" />
          刷新
        </el-button>
      </template>
    </PageHeader>

    <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon @close="errorMessage = ''" />

    <div class="metric-grid audit-metrics">
      <article v-for="metric in metrics" :key="metric.label" class="metric-card">
        <span :class="['metric-icon', metric.tone]"><component :is="metric.icon" :size="21" /></span>
        <div>
          <span>{{ metric.label }}</span>
          <strong>{{ metric.value.toLocaleString() }}</strong>
        </div>
      </article>
    </div>

    <section class="content-section audit-section">
      <div class="audit-filter-bar">
        <el-select v-model="filters.event" clearable placeholder="全部事件" @change="applyFilters">
          <el-option v-for="item in eventOptions" :key="item[0]" :label="item[1]" :value="item[0]" />
        </el-select>
        <el-select v-model="filters.outcome" clearable placeholder="全部结果" @change="applyFilters">
          <el-option label="成功" value="success" />
          <el-option label="失败" value="failed" />
        </el-select>
        <el-button @click="resetFilters">重置</el-button>
        <span class="audit-result-count">共 {{ total }} 条记录</span>
      </div>

      <el-table v-loading="loading" :data="logs" size="small" empty-text="暂无审计记录">
        <el-table-column label="时间" width="180">
          <template #default="scope">{{ new Date(scope.row.created_at).toLocaleString('zh-CN') }}</template>
        </el-table-column>
        <el-table-column label="事件" width="150">
          <template #default="scope">{{ eventLabels[scope.row.event] || scope.row.event }}</template>
        </el-table-column>
        <el-table-column label="结果" width="90">
          <template #default="scope">
            <el-tag :type="scope.row.outcome === 'success' ? 'success' : 'danger'" size="small">
              {{ scope.row.outcome === 'success' ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作用户" width="150">
          <template #default="scope">{{ scope.row.actor_name || '匿名/未知' }}</template>
        </el-table-column>
        <el-table-column label="IP" width="140">
          <template #default="scope">{{ scope.row.client_ip || '-' }}</template>
        </el-table-column>
        <el-table-column label="操作详情" min-width="320" show-overflow-tooltip>
          <template #default="scope">{{ formatDetails(scope.row.details) }}</template>
        </el-table-column>
      </el-table>

      <div class="audit-pagination">
        <el-pagination
          v-model:current-page="filters.page"
          :page-size="filters.page_size"
          :total="total"
          layout="prev, pager, next"
          @current-change="loadData"
        />
      </div>
    </section>
  </section>
</template>

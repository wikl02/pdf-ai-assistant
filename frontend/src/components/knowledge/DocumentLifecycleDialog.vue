<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Clock3, FileClock, FileUp, RefreshCw } from '@lucide/vue'
import type { UploadFile, UploadUserFile } from 'element-plus'

import DocumentStatusTag from '../common/DocumentStatusTag.vue'
import type { DocumentLifecycle, IndexTaskStatus, IndexTaskTrigger } from '../../types'

const props = defineProps<{
  modelValue: boolean
  lifecycle: DocumentLifecycle | null
  loading: boolean
  uploadLoading: boolean
}>()
const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  refresh: []
  uploadVersion: [file: File]
}>()

const fileList = ref<UploadUserFile[]>([])
const selectedFile = ref<File | null>(null)
const currentError = computed(() => props.lifecycle?.document.error_message || '')

const triggerLabels: Record<IndexTaskTrigger, string> = {
  upload: '首次上传',
  version_upload: '上传新版本',
  reindex: '重新索引',
}
const taskLabels: Record<IndexTaskStatus, string> = {
  pending: '等待中',
  processing: '处理中',
  succeeded: '成功',
  failed: '失败',
}

function handleFileChange(file: UploadFile) {
  selectedFile.value = file.raw || null
  fileList.value = file.raw ? [file] : []
}

function submitVersion() {
  if (selectedFile.value) emit('uploadVersion', selectedFile.value)
}

function formatTime(value: string | null) {
  return value ? new Date(value).toLocaleString('zh-CN') : '-'
}

watch(() => props.modelValue, (open) => {
  if (!open) {
    selectedFile.value = null
    fileList.value = []
  }
})
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    title="文档生命周期"
    width="880px"
    class="responsive-dialog lifecycle-dialog"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div v-loading="loading" class="lifecycle-content">
      <template v-if="lifecycle">
        <div class="lifecycle-summary">
          <div>
            <span>当前文档</span>
            <strong>{{ lifecycle.document.filename }}</strong>
          </div>
          <div>
            <span>当前版本</span>
            <strong>V{{ lifecycle.document.current_version_number }}</strong>
          </div>
          <div>
            <span>处理状态</span>
            <DocumentStatusTag :status="lifecycle.document.status" />
          </div>
          <el-button :loading="loading" @click="emit('refresh')">
            <RefreshCw :size="15" />刷新
          </el-button>
        </div>

        <el-alert
          v-if="currentError"
          :title="`最近一次处理失败：${currentError}`"
          type="error"
          show-icon
          :closable="false"
        />

        <section class="lifecycle-section">
          <div class="lifecycle-heading">
            <div><FileClock :size="18" /><strong>版本记录</strong></div>
            <el-upload
              v-model:file-list="fileList"
              action="#"
              :auto-upload="false"
              :limit="1"
              :on-change="handleFileChange"
            >
              <el-button><FileUp :size="15" />选择新版本</el-button>
            </el-upload>
          </div>
          <el-table :data="lifecycle.versions" size="small" max-height="230">
            <el-table-column label="版本" width="75">
              <template #default="scope">V{{ scope.row.version_number }}</template>
            </el-table-column>
            <el-table-column prop="filename" label="文件名" min-width="180" show-overflow-tooltip />
            <el-table-column label="状态" width="90">
              <template #default="scope"><DocumentStatusTag :status="scope.row.status" /></template>
            </el-table-column>
            <el-table-column prop="chunk_count" label="文本块" width="80" align="right" />
            <el-table-column label="创建时间" width="170">
              <template #default="scope">{{ formatTime(scope.row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="失败原因" min-width="150" show-overflow-tooltip>
              <template #default="scope">{{ scope.row.error_message || '-' }}</template>
            </el-table-column>
          </el-table>
          <div v-if="selectedFile" class="version-submit-row">
            <span>将创建 V{{ lifecycle.document.current_version_number + 1 }}，旧版本文件会保留。</span>
            <el-button type="primary" :loading="uploadLoading" @click="submitVersion">上传并建立索引</el-button>
          </div>
        </section>

        <section class="lifecycle-section">
          <div class="lifecycle-heading"><div><Clock3 :size="18" /><strong>索引任务记录</strong></div></div>
          <el-table :data="lifecycle.index_tasks" size="small" max-height="260">
            <el-table-column label="任务" width="110">
              <template #default="scope">{{ triggerLabels[scope.row.trigger as IndexTaskTrigger] }}</template>
            </el-table-column>
            <el-table-column label="版本" width="70">
              <template #default="scope">V{{ scope.row.version_number }}</template>
            </el-table-column>
            <el-table-column label="状态" width="90">
              <template #default="scope">
                <el-tag :type="scope.row.status === 'succeeded' ? 'success' : scope.row.status === 'failed' ? 'danger' : 'warning'" size="small">
                  {{ taskLabels[scope.row.status as IndexTaskStatus] }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="chunk_count" label="文本块" width="80" align="right" />
            <el-table-column label="耗时" width="90">
              <template #default="scope">{{ scope.row.duration_ms === null ? '-' : `${scope.row.duration_ms} ms` }}</template>
            </el-table-column>
            <el-table-column label="执行时间" width="170">
              <template #default="scope">{{ formatTime(scope.row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="失败原因" min-width="170" show-overflow-tooltip>
              <template #default="scope">{{ scope.row.error_message || '-' }}</template>
            </el-table-column>
          </el-table>
        </section>
      </template>
    </div>
  </el-dialog>
</template>

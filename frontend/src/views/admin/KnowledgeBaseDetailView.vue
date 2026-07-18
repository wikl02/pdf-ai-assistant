<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, FileUp, RefreshCw, RotateCw, Trash2 } from '@lucide/vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import { getErrorMessage } from '../../api/http'
import {
  deleteDocumentApi,
  getKnowledgeBaseApi,
  reindexDocumentApi,
  uploadDocumentsApi,
} from '../../api/knowledge'
import DocumentStatusTag from '../../components/common/DocumentStatusTag.vue'
import EmptyState from '../../components/common/EmptyState.vue'
import PageHeader from '../../components/common/PageHeader.vue'
import DocumentUploadDialog from '../../components/knowledge/DocumentUploadDialog.vue'
import type { KnowledgeBaseDetail } from '../../types'

const route = useRoute()
const router = useRouter()
const knowledgeBaseId = computed(() => Number(route.params.id))
const knowledgeBase = ref<KnowledgeBaseDetail | null>(null)
const loading = ref(true)
const uploading = ref(false)
const uploadDialogOpen = ref(false)
const errorMessage = ref('')
const processingDocumentId = ref<number | null>(null)

function formatSize(size: number) {
  return size < 1024 * 1024
    ? `${(size / 1024).toFixed(1)} KB`
    : `${(size / 1024 / 1024).toFixed(1)} MB`
}

async function loadDetail() {
  loading.value = true
  errorMessage.value = ''
  try {
    knowledgeBase.value = await getKnowledgeBaseApi(knowledgeBaseId.value)
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '知识库详情加载失败')
  } finally {
    loading.value = false
  }
}

async function upload(files: File[]) {
  uploading.value = true
  try {
    await uploadDocumentsApi(knowledgeBaseId.value, files)
    ElMessage.success('文档上传并建立索引成功')
    uploadDialogOpen.value = false
    await loadDetail()
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '文档上传失败'))
  } finally {
    uploading.value = false
  }
}

async function removeDocument(documentId: number, filename: string) {
  try {
    await ElMessageBox.confirm(
      `确定删除“${filename}”吗？该文档对应的向量文本块也会被清理。`,
      '删除文档',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
    processingDocumentId.value = documentId
    await deleteDocumentApi(knowledgeBaseId.value, documentId)
    ElMessage.success('文档已删除')
    await loadDetail()
  } catch (error) {
    if (error === 'cancel' || error === 'close') return
    ElMessage.error(getErrorMessage(error, '文档删除失败'))
  } finally {
    processingDocumentId.value = null
  }
}

async function reindex(documentId: number) {
  processingDocumentId.value = documentId
  try {
    await reindexDocumentApi(knowledgeBaseId.value, documentId)
    ElMessage.success('文档索引已更新')
    await loadDetail()
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '重新索引失败'))
  } finally {
    processingDocumentId.value = null
  }
}

onMounted(loadDetail)
</script>

<template>
  <section>
    <button class="back-button" @click="router.push('/admin/knowledge-bases')">
      <ArrowLeft :size="16" />
      返回知识库列表
    </button>
    <PageHeader
      :title="knowledgeBase?.name || '知识库详情'"
      :description="knowledgeBase?.description || '查看并维护知识库文档。'"
    >
      <template #actions>
        <el-button :loading="loading" @click="loadDetail">
          <RefreshCw :size="16" />
          刷新
        </el-button>
        <el-button type="primary" @click="uploadDialogOpen = true">
          <FileUp :size="17" />
          上传文档
        </el-button>
      </template>
    </PageHeader>

    <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon @close="errorMessage = ''" />

    <div v-if="knowledgeBase" class="summary-strip">
      <div><span>文档数量</span><strong>{{ knowledgeBase.document_count }}</strong></div>
      <div><span>文本块数量</span><strong>{{ knowledgeBase.chunk_count }}</strong></div>
      <div class="collection-value"><span>Collection</span><code>{{ knowledgeBase.collection_name }}</code></div>
      <div><span>最近更新</span><strong>{{ new Date(knowledgeBase.updated_at).toLocaleString('zh-CN') }}</strong></div>
    </div>

    <section v-loading="loading" class="content-section table-section">
      <div class="section-heading">
        <div>
          <h2>知识库文档</h2>
          <p>查看处理状态、文本块数量并维护索引。</p>
        </div>
      </div>
      <el-table v-if="knowledgeBase?.documents.length" :data="knowledgeBase.documents" size="small" row-key="id">
        <el-table-column label="文件" min-width="230">
          <template #default="scope">
            <div class="primary-cell">
              <strong>{{ scope.row.filename }}</strong>
              <span>{{ scope.row.file_type.toUpperCase() }} · {{ formatSize(scope.row.file_size) }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="scope">
            <DocumentStatusTag :status="scope.row.status" />
          </template>
        </el-table-column>
        <el-table-column prop="chunk_count" label="文本块" width="100" align="right" />
        <el-table-column label="上传时间" width="180">
          <template #default="scope">{{ new Date(scope.row.created_at).toLocaleString('zh-CN') }}</template>
        </el-table-column>
        <el-table-column label="操作" width="190" fixed="right">
          <template #default="scope">
            <el-button
              text
              type="primary"
              :loading="processingDocumentId === scope.row.id"
              @click="reindex(scope.row.id)"
            >
              <RotateCw :size="15" />
              重新索引
            </el-button>
            <el-button
              text
              type="danger"
              :disabled="processingDocumentId === scope.row.id"
              @click="removeDocument(scope.row.id, scope.row.filename)"
            >
              <Trash2 :size="15" />
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <EmptyState
        v-else-if="!loading"
        title="暂无文档"
        description="上传文档后，系统会自动解析内容并建立向量索引。"
      >
        <el-button type="primary" @click="uploadDialogOpen = true">
          <FileUp :size="16" />
          上传文档
        </el-button>
      </EmptyState>
    </section>

    <DocumentUploadDialog
      v-model="uploadDialogOpen"
      :loading="uploading"
      @submit="upload"
    />
  </section>
</template>

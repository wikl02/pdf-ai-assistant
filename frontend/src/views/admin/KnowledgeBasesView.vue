<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowRight, Plus, RefreshCw } from '@lucide/vue'
import { ElMessage } from 'element-plus'

import { getErrorMessage } from '../../api/http'
import { createKnowledgeBaseApi, listAdminKnowledgeBasesApi } from '../../api/knowledge'
import EmptyState from '../../components/common/EmptyState.vue'
import PageHeader from '../../components/common/PageHeader.vue'
import KnowledgeBaseCreateDialog from '../../components/knowledge/KnowledgeBaseCreateDialog.vue'
import type { KnowledgeBase } from '../../types'

const router = useRouter()
const loading = ref(true)
const creating = ref(false)
const createDialogOpen = ref(false)
const errorMessage = ref('')
const knowledgeBases = ref<KnowledgeBase[]>([])

async function loadKnowledgeBases() {
  loading.value = true
  errorMessage.value = ''
  try {
    knowledgeBases.value = await listAdminKnowledgeBasesApi()
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '知识库列表加载失败')
  } finally {
    loading.value = false
  }
}

async function createKnowledgeBase(payload: { name: string; description?: string }) {
  creating.value = true
  try {
    const knowledgeBase = await createKnowledgeBaseApi(payload)
    ElMessage.success('知识库创建成功')
    createDialogOpen.value = false
    await router.push(`/admin/knowledge-bases/${knowledgeBase.id}`)
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '知识库创建失败'))
  } finally {
    creating.value = false
  }
}

onMounted(loadKnowledgeBases)
</script>

<template>
  <section>
    <PageHeader title="知识库管理" description="维护企业知识集合及其文档索引。">
      <template #actions>
        <el-button :loading="loading" @click="loadKnowledgeBases">
          <RefreshCw :size="16" />
          刷新
        </el-button>
        <el-button type="primary" @click="createDialogOpen = true">
          <Plus :size="17" />
          创建知识库
        </el-button>
      </template>
    </PageHeader>

    <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon @close="errorMessage = ''" />

    <section v-loading="loading" class="content-section table-section">
      <el-table v-if="knowledgeBases.length" :data="knowledgeBases" size="small" row-key="id">
        <el-table-column label="知识库" min-width="250">
          <template #default="scope">
            <div class="primary-cell">
              <strong>{{ scope.row.name }}</strong>
              <span>{{ scope.row.description || '暂无说明' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="document_count" label="文档" width="100" align="right" />
        <el-table-column prop="chunk_count" label="文本块" width="110" align="right" />
        <el-table-column label="更新时间" width="180">
          <template #default="scope">{{ new Date(scope.row.updated_at).toLocaleString('zh-CN') }}</template>
        </el-table-column>
        <el-table-column label="操作" width="110" fixed="right">
          <template #default="scope">
            <el-button text type="primary" @click="router.push(`/admin/knowledge-bases/${scope.row.id}`)">
              查看 <ArrowRight :size="15" />
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <EmptyState v-else-if="!loading" title="暂无知识库" description="创建知识库后即可上传并索引企业文档。">
        <el-button type="primary" @click="createDialogOpen = true">
          <Plus :size="16" />
          创建知识库
        </el-button>
      </EmptyState>
    </section>

    <KnowledgeBaseCreateDialog
      v-model="createDialogOpen"
      :loading="creating"
      @submit="createKnowledgeBase"
    />
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { BookOpen, Files, MessageSquareText, Plus, Users } from '@lucide/vue'

import { getErrorMessage } from '../../api/http'
import { listAdminKnowledgeBasesApi } from '../../api/knowledge'
import { listUsersApi } from '../../api/users'
import EmptyState from '../../components/common/EmptyState.vue'
import PageHeader from '../../components/common/PageHeader.vue'
import type { KnowledgeBase, User } from '../../types'

const router = useRouter()
const loading = ref(true)
const errorMessage = ref('')
const knowledgeBases = ref<KnowledgeBase[]>([])
const users = ref<User[]>([])

const metrics = computed(() => [
  { label: '知识库', value: knowledgeBases.value.length, icon: BookOpen, tone: 'blue' },
  {
    label: '文档',
    value: knowledgeBases.value.reduce((sum, item) => sum + item.document_count, 0),
    icon: Files,
    tone: 'green',
  },
  {
    label: '文本块',
    value: knowledgeBases.value.reduce((sum, item) => sum + item.chunk_count, 0),
    icon: MessageSquareText,
    tone: 'amber',
  },
  { label: '用户', value: users.value.length, icon: Users, tone: 'gray' },
])

async function loadDashboard() {
  loading.value = true
  errorMessage.value = ''
  try {
    ;[knowledgeBases.value, users.value] = await Promise.all([
      listAdminKnowledgeBasesApi(),
      listUsersApi(),
    ])
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '仪表盘数据加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(loadDashboard)
</script>

<template>
  <section>
    <PageHeader title="仪表盘" description="查看知识库运行概况和近期内容。">
      <template #actions>
        <el-button @click="router.push('/app/chat')">进入知识查询</el-button>
        <el-button type="primary" @click="router.push('/admin/knowledge-bases')">
          <Plus :size="17" />
          新建知识库
        </el-button>
      </template>
    </PageHeader>

    <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon @close="errorMessage = ''" />

    <div v-loading="loading" class="metric-grid">
      <article v-for="metric in metrics" :key="metric.label" class="metric-card">
        <span :class="['metric-icon', metric.tone]"><component :is="metric.icon" :size="21" /></span>
        <div>
          <span>{{ metric.label }}</span>
          <strong>{{ metric.value.toLocaleString() }}</strong>
        </div>
      </article>
    </div>

    <section class="content-section">
      <div class="section-heading">
        <div>
          <h2>最近知识库</h2>
          <p>按创建时间显示最近维护的内容。</p>
        </div>
        <el-button text type="primary" @click="router.push('/admin/knowledge-bases')">查看全部</el-button>
      </div>

      <el-table v-if="knowledgeBases.length" :data="knowledgeBases.slice(0, 6)" size="small">
        <el-table-column prop="name" label="名称" min-width="220">
          <template #default="scope">
            <button class="table-link" @click="router.push(`/admin/knowledge-bases/${scope.row.id}`)">
              {{ scope.row.name }}
            </button>
          </template>
        </el-table-column>
        <el-table-column prop="document_count" label="文档" width="100" />
        <el-table-column prop="chunk_count" label="文本块" width="120" />
        <el-table-column label="创建时间" width="180">
          <template #default="scope">{{ new Date(scope.row.created_at).toLocaleString('zh-CN') }}</template>
        </el-table-column>
      </el-table>
      <EmptyState v-else-if="!loading" title="暂无知识库" description="创建第一个知识库后，概况会显示在这里。">
        <el-button type="primary" @click="router.push('/admin/knowledge-bases')">创建知识库</el-button>
      </EmptyState>
    </section>
  </section>
</template>

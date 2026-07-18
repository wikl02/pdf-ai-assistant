<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import { BookOpen, Eraser, MessageSquarePlus, Send, Sparkles } from '@lucide/vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import { askQuestionApi } from '../../api/chat'
import { getErrorMessage } from '../../api/http'
import { listAccessibleKnowledgeBasesApi } from '../../api/knowledge'
import SourceList from '../../components/chat/SourceList.vue'
import EmptyState from '../../components/common/EmptyState.vue'
import type { ChatMessage, KnowledgeBase } from '../../types'

const knowledgeBases = ref<KnowledgeBase[]>([])
const selectedKnowledgeBaseId = ref<number | null>(null)
const messages = ref<ChatMessage[]>([])
const question = ref('')
const loadingKnowledgeBases = ref(true)
const asking = ref(false)
const errorMessage = ref('')
const messageListRef = ref<HTMLElement>()

const selectedKnowledgeBase = computed(() =>
  knowledgeBases.value.find((item) => item.id === selectedKnowledgeBaseId.value),
)

async function loadKnowledgeBases() {
  loadingKnowledgeBases.value = true
  errorMessage.value = ''
  try {
    knowledgeBases.value = await listAccessibleKnowledgeBasesApi()
    const savedId = Number(localStorage.getItem('enterprise_kb_selected_id'))
    const savedExists = knowledgeBases.value.some((item) => item.id === savedId)
    selectedKnowledgeBaseId.value = savedExists ? savedId : knowledgeBases.value[0]?.id || null
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '知识库加载失败')
  } finally {
    loadingKnowledgeBases.value = false
  }
}

function selectKnowledgeBase(id: number) {
  if (selectedKnowledgeBaseId.value === id) return
  selectedKnowledgeBaseId.value = id
  localStorage.setItem('enterprise_kb_selected_id', String(id))
  messages.value = []
}

function createMessage(role: ChatMessage['role'], content: string): ChatMessage {
  return {
    id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    role,
    content,
    status: 'done',
  }
}

async function scrollToBottom() {
  await nextTick()
  messageListRef.value?.scrollTo({ top: messageListRef.value.scrollHeight, behavior: 'smooth' })
}

async function ask() {
  const content = question.value.trim()
  if (!selectedKnowledgeBase.value) {
    ElMessage.warning('请先选择知识库')
    return
  }
  if (!content || asking.value) return

  messages.value.push(createMessage('user', content))
  question.value = ''
  const assistantMessage: ChatMessage = {
    id: `${Date.now()}-assistant`,
    role: 'assistant',
    content: '',
    sources: [],
    status: 'loading',
  }
  messages.value.push(assistantMessage)
  asking.value = true
  await scrollToBottom()

  try {
    const response = await askQuestionApi(selectedKnowledgeBase.value.collection_name, content)
    assistantMessage.content = response.answer
    assistantMessage.sources = response.sources
    assistantMessage.status = 'done'
  } catch (error) {
    assistantMessage.content = getErrorMessage(error, '回答生成失败，请稍后重试')
    assistantMessage.status = 'error'
  } finally {
    asking.value = false
    await scrollToBottom()
  }
}

function newConversation() {
  messages.value = []
  question.value = ''
  ElMessage.success('已创建新会话')
}

async function clearConversation() {
  if (!messages.value.length) return
  try {
    await ElMessageBox.confirm('确定清空当前会话吗？此操作无法撤销。', '清空会话', {
      type: 'warning',
      confirmButtonText: '清空',
      cancelButtonText: '取消',
    })
    messages.value = []
  } catch {
    // User cancelled.
  }
}

onMounted(loadKnowledgeBases)
</script>

<template>
  <div class="query-workspace">
    <aside class="knowledge-selector">
      <div class="selector-heading">
        <div>
          <span>查询范围</span>
          <strong>选择知识库</strong>
        </div>
        <el-button circle text title="刷新知识库" :loading="loadingKnowledgeBases" @click="loadKnowledgeBases">
          <BookOpen :size="17" />
        </el-button>
      </div>

      <el-skeleton v-if="loadingKnowledgeBases" :rows="4" animated />
      <nav v-else-if="knowledgeBases.length" class="knowledge-list">
        <button
          v-for="item in knowledgeBases"
          :key="item.id"
          :class="['knowledge-list-item', { active: item.id === selectedKnowledgeBaseId }]"
          @click="selectKnowledgeBase(item.id)"
        >
          <span class="knowledge-list-icon"><BookOpen :size="17" /></span>
          <span>
            <strong>{{ item.name }}</strong>
            <small>{{ item.document_count }} 个文档 · {{ item.chunk_count }} 个文本块</small>
          </span>
        </button>
      </nav>
      <EmptyState v-else title="暂无可查询知识库" description="请联系管理员添加知识库内容。" />
    </aside>

    <section class="conversation-panel">
      <header class="conversation-header">
        <div>
          <span>当前知识库</span>
          <strong>{{ selectedKnowledgeBase?.name || '尚未选择' }}</strong>
        </div>
        <div class="conversation-actions">
          <el-button @click="newConversation">
            <MessageSquarePlus :size="16" />
            新建会话
          </el-button>
          <el-button :disabled="!messages.length" @click="clearConversation">
            <Eraser :size="16" />
            清空
          </el-button>
        </div>
      </header>

      <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon :closable="false" />

      <div ref="messageListRef" class="message-list">
        <div v-if="!messages.length" class="conversation-empty">
          <span><Sparkles :size="26" /></span>
          <h1>开始查询企业知识</h1>
          <p>{{ selectedKnowledgeBase ? `当前范围：${selectedKnowledgeBase.name}` : '请先选择一个知识库' }}</p>
        </div>

        <article v-for="message in messages" :key="message.id" :class="['chat-message', message.role]">
          <div class="message-avatar">{{ message.role === 'user' ? '我' : 'AI' }}</div>
          <div class="message-body">
            <strong>{{ message.role === 'user' ? '你' : '知识库助手' }}</strong>
            <div v-if="message.status === 'loading'" class="answer-loading">
              <span /><span /><span />
              正在检索知识库
            </div>
            <p v-else :class="{ 'error-answer': message.status === 'error' }">{{ message.content }}</p>
            <SourceList v-if="message.sources?.length" :sources="message.sources" />
          </div>
        </article>
      </div>

      <form class="composer" @submit.prevent="ask">
        <el-input
          v-model="question"
          type="textarea"
          resize="none"
          :autosize="{ minRows: 2, maxRows: 5 }"
          maxlength="5000"
          placeholder="输入需要查询的问题"
          :disabled="!selectedKnowledgeBase || asking"
          @keydown.ctrl.enter.prevent="ask"
        />
        <el-button
          class="send-button"
          type="primary"
          title="发送问题"
          :loading="asking"
          :disabled="!question.trim() || !selectedKnowledgeBase"
          @click="ask"
        >
          <Send :size="18" />
          发送
        </el-button>
      </form>
    </section>
  </div>
</template>

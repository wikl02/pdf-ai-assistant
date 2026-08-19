<script setup lang="ts">
import { computed, nextTick, onMounted, ref, shallowRef } from 'vue'
import {
  Eraser,
  History,
  MessageSquarePlus,
  RefreshCw,
  Send,
  Sparkles,
  Square,
  Trash2,
} from '@lucide/vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import {
  askQuestionApi,
  cancelQuestionApi,
  deleteConversationApi,
  getConversationApi,
  listConversationsApi,
} from '../../api/chat'
import { getErrorMessage, isRequestCancelled } from '../../api/http'
import { listAccessibleKnowledgeBasesApi } from '../../api/knowledge'
import SourceList from '../../components/chat/SourceList.vue'
import EmptyState from '../../components/common/EmptyState.vue'
import type { ChatMessage, ConversationSummary, KnowledgeBase } from '../../types'

const knowledgeBases = ref<KnowledgeBase[]>([])
const selectedKnowledgeBaseId = ref<number | null>(null)
const conversations = ref<ConversationSummary[]>([])
const currentConversationId = ref<number | null>(null)
const messages = ref<ChatMessage[]>([])
const question = ref('')
const loadingKnowledgeBases = ref(true)
const loadingConversations = ref(false)
const loadingMessages = ref(false)
const asking = ref(false)
const stopping = ref(false)
const errorMessage = ref('')
const messageListRef = ref<HTMLElement>()

interface ActiveQuestionRequest {
  id: string
  controller: AbortController
  message: ChatMessage
  cancelled: boolean
}

const activeQuestionRequest = shallowRef<ActiveQuestionRequest | null>(null)

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
    await loadConversations()
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '知识库加载失败')
  } finally {
    loadingKnowledgeBases.value = false
  }
}

async function loadConversations() {
  if (!selectedKnowledgeBaseId.value) {
    conversations.value = []
    return
  }
  loadingConversations.value = true
  try {
    conversations.value = await listConversationsApi(selectedKnowledgeBaseId.value)
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '历史会话加载失败')
  } finally {
    loadingConversations.value = false
  }
}

async function selectKnowledgeBase(id: number) {
  if (selectedKnowledgeBaseId.value === id || asking.value) return
  selectedKnowledgeBaseId.value = id
  localStorage.setItem('enterprise_kb_selected_id', String(id))
  newConversation(false)
  await loadConversations()
}

async function openConversation(id: number) {
  if (currentConversationId.value === id || loadingMessages.value || asking.value) return
  loadingMessages.value = true
  errorMessage.value = ''
  try {
    const detail = await getConversationApi(id)
    currentConversationId.value = id
    selectedKnowledgeBaseId.value = detail.knowledge_base_id
    messages.value = detail.messages.map((message) => ({
      id: message.id,
      role: message.role,
      content: message.content,
      sources: message.sources || [],
      status: message.status === 'failed'
        ? 'error'
        : message.status === 'cancelled' ? 'cancelled' : 'done',
      response_time_ms: message.response_time_ms,
      llm_model: message.llm_model,
      prompt_tokens: message.prompt_tokens,
      completion_tokens: message.completion_tokens,
      total_tokens: message.total_tokens,
      created_at: message.created_at,
    }))
    await scrollToBottom(false)
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '会话内容加载失败')
  } finally {
    loadingMessages.value = false
  }
}

function createMessage(role: ChatMessage['role'], content: string): ChatMessage {
  return {
    id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    role,
    content,
    status: 'done',
  }
}

async function scrollToBottom(smooth = true) {
  await nextTick()
  messageListRef.value?.scrollTo({
    top: messageListRef.value.scrollHeight,
    behavior: smooth ? 'smooth' : 'auto',
  })
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
  const activeRequest: ActiveQuestionRequest = {
    id: globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    controller: new AbortController(),
    message: assistantMessage,
    cancelled: false,
  }
  activeQuestionRequest.value = activeRequest
  asking.value = true
  await scrollToBottom()

  try {
    const response = await askQuestionApi(
      selectedKnowledgeBase.value.collection_name,
      content,
      currentConversationId.value,
      activeRequest.id,
      activeRequest.controller.signal,
    )
    if (activeRequest.cancelled) return
    currentConversationId.value = response.conversation_id
    assistantMessage.id = response.assistant_message_id || assistantMessage.id
    assistantMessage.content = response.answer
    assistantMessage.sources = response.sources
    assistantMessage.llm_model = response.llm_model
    assistantMessage.prompt_tokens = response.prompt_tokens
    assistantMessage.completion_tokens = response.completion_tokens
    assistantMessage.total_tokens = response.total_tokens
    assistantMessage.status = 'done'
    await loadConversations()
  } catch (error) {
    if (!activeRequest.cancelled && !isRequestCancelled(error)) {
      assistantMessage.content = getErrorMessage(error, '回答生成失败，请稍后重试')
      assistantMessage.status = 'error'
      await loadConversations()
    }
  } finally {
    if (activeQuestionRequest.value === activeRequest) {
      activeQuestionRequest.value = null
      asking.value = false
      stopping.value = false
    }
    await scrollToBottom()
  }
}

async function stopAnswer() {
  const activeRequest = activeQuestionRequest.value
  if (!activeRequest || stopping.value) return

  activeRequest.cancelled = true
  activeRequest.message.content = '回答已停止。'
  activeRequest.message.status = 'cancelled'
  stopping.value = true
  try {
    const response = await cancelQuestionApi(activeRequest.id)
    if (response.conversation_id) currentConversationId.value = response.conversation_id
    if (response.assistant_message_id) {
      activeRequest.message.id = response.assistant_message_id
    }
    if (!response.cancelled) {
      ElMessage.info('该回答已经结束，无需再次停止')
    }
  } catch (error) {
    ElMessage.warning(getErrorMessage(error, '页面已停止等待，但后端取消状态暂时无法确认'))
  } finally {
    activeRequest.controller.abort()
    if (activeQuestionRequest.value === activeRequest) {
      activeQuestionRequest.value = null
      asking.value = false
      stopping.value = false
    }
    await new Promise((resolve) => window.setTimeout(resolve, 200))
    await loadConversations()
    await scrollToBottom()
  }
}

function newConversation(showMessage = true) {
  if (asking.value) return
  currentConversationId.value = null
  messages.value = []
  question.value = ''
  if (showMessage) ElMessage.success('已准备新会话')
}

async function removeConversation(id: number) {
  try {
    await ElMessageBox.confirm('确定删除这条历史会话吗？删除后无法恢复。', '删除会话', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
    await deleteConversationApi(id)
    if (currentConversationId.value === id) newConversation(false)
    await loadConversations()
    ElMessage.success('会话已删除')
  } catch (error) {
    if (error === 'cancel' || error === 'close') return
    ElMessage.error(getErrorMessage(error, '删除会话失败'))
  }
}

async function clearConversation() {
  if (!messages.value.length) return
  if (currentConversationId.value) {
    await removeConversation(currentConversationId.value)
    return
  }
  newConversation(false)
}

onMounted(loadKnowledgeBases)
</script>

<template>
  <div class="query-workspace">
    <aside class="conversation-sidebar">
      <div class="knowledge-picker">
        <label for="knowledge-base-select">查询知识库</label>
        <el-select
          id="knowledge-base-select"
          :model-value="selectedKnowledgeBaseId"
          :loading="loadingKnowledgeBases"
          :disabled="asking"
          placeholder="选择知识库"
          @change="selectKnowledgeBase"
        >
          <el-option
            v-for="item in knowledgeBases"
            :key="item.id"
            :label="item.name"
            :value="item.id"
          />
        </el-select>
      </div>

      <div class="history-heading">
        <div>
          <History :size="16" />
          <strong>历史会话</strong>
        </div>
        <el-button circle text title="刷新历史" :loading="loadingConversations" :disabled="asking" @click="loadConversations">
          <RefreshCw :size="16" />
        </el-button>
      </div>

      <el-button class="new-conversation-button" type="primary" plain :disabled="asking" @click="newConversation()">
        <MessageSquarePlus :size="16" />
        新建会话
      </el-button>

      <div v-loading="loadingConversations" class="history-list">
        <div
          v-for="item in conversations"
          :key="item.id"
          :class="['history-item', { active: item.id === currentConversationId }]"
          role="button"
          tabindex="0"
          @click="openConversation(item.id)"
          @keydown.enter="openConversation(item.id)"
        >
          <span>
            <strong>{{ item.title }}</strong>
            <small>{{ item.message_count }} 条消息 · {{ new Date(item.updated_at).toLocaleDateString('zh-CN') }}</small>
          </span>
          <button
            class="history-delete"
            type="button"
            title="删除会话"
            :disabled="asking"
            @click.stop="removeConversation(item.id)"
          >
            <Trash2 :size="14" />
          </button>
        </div>
        <EmptyState
          v-if="!loadingConversations && !conversations.length"
          title="暂无历史会话"
          description="发送第一个问题后，会话会保存在这里。"
        />
      </div>
    </aside>

    <section class="conversation-panel">
      <header class="conversation-header">
        <div>
          <span>当前知识库</span>
          <strong>{{ selectedKnowledgeBase?.name || '尚未选择' }}</strong>
        </div>
        <div class="conversation-actions">
          <el-button :disabled="asking" @click="newConversation()">
            <MessageSquarePlus :size="16" />
            新建会话
          </el-button>
          <el-button :disabled="!messages.length || asking" @click="clearConversation">
            <Eraser :size="16" />
            删除当前会话
          </el-button>
        </div>
      </header>

      <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon closable @close="errorMessage = ''" />

      <div ref="messageListRef" v-loading="loadingMessages" class="message-list">
        <div v-if="!messages.length && !loadingMessages" class="conversation-empty">
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
            <p
              v-else
              :class="{
                'error-answer': message.status === 'error',
                'cancelled-answer': message.status === 'cancelled',
              }"
            >{{ message.content }}</p>
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
          v-if="asking"
          class="send-button stop-button"
          type="danger"
          plain
          native-type="button"
          title="停止回答"
          :loading="stopping"
          @click="stopAnswer"
        >
          <Square :size="16" fill="currentColor" />
          停止
        </el-button>
        <el-button
          v-else
          class="send-button"
          type="primary"
          title="发送问题"
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

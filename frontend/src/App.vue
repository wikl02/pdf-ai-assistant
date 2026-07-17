<script setup>
import { computed, ref } from 'vue'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const username = ref('')
const password = ref('')
const accessToken = ref('')
const currentUsername = ref('')
const loginError = ref('')
const loginLoading = ref(false)

const selectedFiles = ref([])
const uploadLoading = ref(false)
const uploadError = ref('')
const collectionId = ref('')
const documents = ref([])
const chunkCount = ref(0)

const question = ref('')
const askLoading = ref(false)
const askError = ref('')
const messages = ref([])

const backendStatus = ref('未检查')

const isLoggedIn = computed(() => Boolean(accessToken.value))
const hasKnowledgeBase = computed(() => Boolean(collectionId.value))

function authHeaders() {
  return {
    Authorization: `Bearer ${accessToken.value}`,
  }
}

async function parseError(response) {
  try {
    const data = await response.json()
    return typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail)
  } catch {
    return '请求失败，请稍后再试。'
  }
}

async function checkBackend() {
  backendStatus.value = '检查中'
  try {
    const response = await fetch(`${API_BASE_URL}/health`)
    backendStatus.value = response.ok ? '运行正常' : `异常：${response.status}`
  } catch {
    backendStatus.value = '无法连接'
  }
}

async function login() {
  loginError.value = ''

  if (!username.value.trim() || !password.value) {
    loginError.value = '请输入用户名和密码。'
    return
  }

  loginLoading.value = true
  try {
    const response = await fetch(`${API_BASE_URL}/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: username.value.trim(),
        password: password.value,
      }),
    })

    if (!response.ok) {
      loginError.value = await parseError(response)
      return
    }

    const data = await response.json()
    accessToken.value = data.access_token
    currentUsername.value = username.value.trim()
    password.value = ''
  } catch {
    loginError.value = '无法连接 FastAPI 后端，请确认后端已启动。'
  } finally {
    loginLoading.value = false
  }
}

function logout() {
  accessToken.value = ''
  currentUsername.value = ''
  collectionId.value = ''
  documents.value = []
  chunkCount.value = 0
  messages.value = []
}

function handleFileChange(event) {
  selectedFiles.value = Array.from(event.target.files || [])
  uploadError.value = ''
}

async function uploadDocuments() {
  uploadError.value = ''

  if (!selectedFiles.value.length) {
    uploadError.value = '请先选择至少一个文档。'
    return
  }

  const formData = new FormData()
  selectedFiles.value.forEach((file) => formData.append('files', file))

  uploadLoading.value = true
  try {
    const response = await fetch(`${API_BASE_URL}/upload`, {
      method: 'POST',
      headers: authHeaders(),
      body: formData,
    })

    if (!response.ok) {
      uploadError.value = await parseError(response)
      return
    }

    const data = await response.json()
    collectionId.value = data.collection_id
    documents.value = data.documents
    chunkCount.value = data.chunk_count
    messages.value = []
  } catch {
    uploadError.value = '上传失败：无法连接 FastAPI 后端。'
  } finally {
    uploadLoading.value = false
  }
}

async function askQuestion() {
  askError.value = ''
  const questionText = question.value.trim()

  if (!collectionId.value) {
    askError.value = '请先构建知识库。'
    return
  }

  if (!questionText) {
    askError.value = '请输入问题。'
    return
  }

  messages.value.unshift({ role: 'user', content: questionText })
  question.value = ''
  askLoading.value = true

  try {
    const response = await fetch(`${API_BASE_URL}/ask`, {
      method: 'POST',
      headers: {
        ...authHeaders(),
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        collection_id: collectionId.value,
        question: questionText,
      }),
    })

    if (!response.ok) {
      const error = await parseError(response)
      messages.value.unshift({ role: 'assistant', content: error, sources: [] })
      return
    }

    const data = await response.json()
    messages.value.unshift({
      role: 'assistant',
      content: data.answer,
      sources: data.sources || [],
    })
  } catch {
    messages.value.unshift({
      role: 'assistant',
      content: '请求失败：无法连接 FastAPI 后端。',
      sources: [],
    })
  } finally {
    askLoading.value = false
  }
}

function formatSource(metadata) {
  if (!metadata) return '未知来源'

  if (metadata.location_type === 'page_line') {
    return `${metadata.source_name}，第 ${metadata.page} 页，第 ${metadata.start_line}-${metadata.end_line} 行`
  }
  if (metadata.location_type === 'paragraph') {
    return `${metadata.source_name}，第 ${metadata.start_line} 段`
  }
  if (metadata.location_type === 'row') {
    return `${metadata.source_name}，第 ${metadata.start_line} 行`
  }
  if (metadata.location_type === 'sheet_row') {
    return `${metadata.source_name}，${metadata.sheet || '工作表'}，第 ${metadata.start_line} 行`
  }
  if (metadata.location_type === 'line') {
    return `${metadata.source_name}，第 ${metadata.start_line}-${metadata.end_line} 行`
  }
  return metadata.source_name || '未知来源'
}
</script>

<template>
  <main class="page-shell">
    <aside class="sidebar">
      <div>
        <p class="eyebrow">Enterprise knowledge base</p>
        <h1>企业知识库智能助手</h1>
      </div>

      <div class="status-card">
        <span>后端地址</span>
        <strong>{{ API_BASE_URL }}</strong>
        <button class="secondary-button" @click="checkBackend">检查后端</button>
        <p class="status-line">状态：{{ backendStatus }}</p>
      </div>

      <div v-if="isLoggedIn" class="status-card">
        <span>当前用户</span>
        <strong>{{ currentUsername }}</strong>
        <button class="secondary-button" @click="logout">退出登录</button>
      </div>
    </aside>

    <section class="content">
      <section v-if="!isLoggedIn" class="panel login-panel">
        <h2>账号登录</h2>
        <p>登录后才能上传文档和调用知识库问答接口。</p>
        <form class="form-stack" @submit.prevent="login">
          <label>
            用户名
            <input v-model="username" autocomplete="username" />
          </label>
          <label>
            密码
            <input v-model="password" type="password" autocomplete="current-password" />
          </label>
          <button type="submit" :disabled="loginLoading">
            {{ loginLoading ? '登录中...' : '登录' }}
          </button>
          <p v-if="loginError" class="error-text">{{ loginError }}</p>
        </form>
      </section>

      <template v-else>
        <section class="panel upload-panel">
          <div class="panel-header">
            <div>
              <h2>构建知识库</h2>
              <p>选择 PDF、TXT、Markdown、DOCX、CSV 或 XLSX 文档。</p>
            </div>
            <button :disabled="uploadLoading" @click="uploadDocuments">
              {{ uploadLoading ? '构建中...' : '构建知识库' }}
            </button>
          </div>

          <input
            class="file-input"
            type="file"
            multiple
            accept=".pdf,.txt,.md,.docx,.csv,.xlsx"
            @change="handleFileChange"
          />

          <div v-if="selectedFiles.length" class="file-list">
            <div v-for="file in selectedFiles" :key="file.name" class="file-pill">
              <span>{{ file.name }}</span>
              <small>{{ (file.size / 1024).toFixed(1) }} KB</small>
            </div>
          </div>

          <p v-if="uploadError" class="error-text">{{ uploadError }}</p>

          <div v-if="collectionId" class="success-box">
            <strong>知识库已就绪</strong>
            <span>{{ documents.length }} 个文档，{{ chunkCount }} 个文本块</span>
            <code>{{ collectionId }}</code>
          </div>
        </section>

        <section v-if="documents.length" class="panel compact-panel">
          <h2>已上传文档</h2>
          <div class="document-grid">
            <div v-for="document in documents" :key="document.name" class="document-card">
              <strong>{{ document.name }}</strong>
              <span>{{ document.type }} · {{ (document.size / 1024).toFixed(1) }} KB</span>
            </div>
          </div>
        </section>

        <section class="panel ask-panel">
          <h2>知识库问答</h2>
          <form class="ask-row" @submit.prevent="askQuestion">
            <input v-model="question" placeholder="请输入你想问知识库的问题" />
            <button type="submit" :disabled="askLoading">
              {{ askLoading ? '思考中...' : '提交问题' }}
            </button>
          </form>
          <p v-if="askError" class="error-text">{{ askError }}</p>
        </section>

        <section v-if="messages.length" class="panel chat-panel">
          <h2>聊天记录</h2>
          <article v-for="(message, index) in messages" :key="index" :class="['message', message.role]">
            <div class="message-role">{{ message.role === 'user' ? '用户' : '助手' }}</div>
            <p>{{ message.content }}</p>

            <details v-if="message.sources?.length">
              <summary>查看检索到的 {{ message.sources.length }} 个文本块</summary>
              <div v-for="source in message.sources" :key="source.metadata.chunk_id" class="source-box">
                <strong>{{ formatSource(source.metadata) }}</strong>
                <span>文本块 {{ source.metadata.chunk_id }} · 相似度 {{ source.score }}</span>
                <p>{{ source.text }}</p>
              </div>
            </details>
          </article>
        </section>
      </template>
    </section>
  </main>
</template>

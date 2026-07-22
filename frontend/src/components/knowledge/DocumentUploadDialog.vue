<script setup lang="ts">
import { ref, watch } from 'vue'
import { FileUp, X } from '@lucide/vue'

const SUPPORTED_EXTENSIONS = new Set(['pdf', 'txt', 'md', 'docx', 'csv', 'xlsx'])
const MAX_TOTAL_SIZE = 50 * 1024 * 1024

const props = defineProps<{ modelValue: boolean; loading: boolean }>()
const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  submit: [files: File[]]
}>()

const files = ref<File[]>([])
const inputRef = ref<HTMLInputElement>()
const dragActive = ref(false)
const validationMessage = ref('')

watch(
  () => props.modelValue,
  (visible) => {
    if (visible) {
      files.value = []
      dragActive.value = false
      validationMessage.value = ''
      if (inputRef.value) inputRef.value.value = ''
    }
  },
)

function addFiles(incomingFiles: File[]) {
  validationMessage.value = ''
  const unsupported = incomingFiles.filter((file) => {
    const extension = file.name.split('.').pop()?.toLowerCase() || ''
    return !SUPPORTED_EXTENSIONS.has(extension)
  })
  if (unsupported.length) {
    validationMessage.value = `不支持以下文件：${unsupported.map((file) => file.name).join('、')}`
  }

  const supported = incomingFiles.filter((file) => {
    const extension = file.name.split('.').pop()?.toLowerCase() || ''
    return SUPPORTED_EXTENSIONS.has(extension)
  })
  const existingKeys = new Set(
    files.value.map((file) => `${file.name}-${file.size}-${file.lastModified}`),
  )
  const additions = supported.filter(
    (file) => !existingKeys.has(`${file.name}-${file.size}-${file.lastModified}`),
  )
  const nextFiles = [...files.value, ...additions]
  const totalSize = nextFiles.reduce((total, file) => total + file.size, 0)
  if (totalSize > MAX_TOTAL_SIZE) {
    validationMessage.value = '单次上传文件总大小不能超过 50 MB，请分批上传。'
    return
  }
  files.value = nextFiles
}

function selectFiles(event: Event) {
  const input = event.target as HTMLInputElement
  addFiles(Array.from(input.files || []))
  input.value = ''
}

function dropFiles(event: DragEvent) {
  dragActive.value = false
  if (props.loading) return
  addFiles(Array.from(event.dataTransfer?.files || []))
}

function removeFile(index: number) {
  files.value.splice(index, 1)
  validationMessage.value = ''
}

function closeDialog() {
  if (!props.loading) emit('update:modelValue', false)
}

function submitFiles() {
  if (!props.loading && files.value.length) emit('submit', [...files.value])
}

function formatSize(size: number) {
  return size < 1024 * 1024
    ? `${(size / 1024).toFixed(1)} KB`
    : `${(size / 1024 / 1024).toFixed(1)} MB`
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    title="上传知识库文档"
    width="620px"
    class="responsive-dialog"
    :close-on-click-modal="!loading"
    :close-on-press-escape="!loading"
    :show-close="!loading"
    @update:model-value="closeDialog"
  >
    <button
      class="upload-dropzone"
      :class="{ 'is-dragging': dragActive }"
      type="button"
      :disabled="loading"
      @click="inputRef?.click()"
      @dragenter.prevent="dragActive = true"
      @dragover.prevent="dragActive = true"
      @dragleave.prevent="dragActive = false"
      @drop.prevent="dropFiles"
    >
      <FileUp :size="28" />
      <strong>点击选择，或将文档拖到这里</strong>
      <span>支持 PDF、TXT、MD、DOCX、CSV、XLSX</span>
    </button>
    <input
      ref="inputRef"
      class="visually-hidden"
      type="file"
      multiple
      accept=".pdf,.txt,.md,.docx,.csv,.xlsx"
      @change="selectFiles"
    />

    <el-alert
      v-if="validationMessage"
      class="upload-message"
      :title="validationMessage"
      type="warning"
      show-icon
      @close="validationMessage = ''"
    />

    <el-alert
      v-if="loading"
      class="upload-message"
      title="正在上传、解析并建立索引，较大文档或首次加载模型可能需要数分钟，请勿重复提交。"
      type="info"
      :closable="false"
      show-icon
    />

    <div v-if="files.length" class="selected-file-list">
      <div v-for="(file, index) in files" :key="`${file.name}-${file.size}`" class="selected-file-item">
        <div>
          <strong>{{ file.name }}</strong>
          <span>{{ formatSize(file.size) }}</span>
        </div>
        <button class="icon-button" title="移除文件" :disabled="loading" @click="removeFile(index)">
          <X :size="17" />
        </button>
      </div>
    </div>

    <template #footer>
      <el-button :disabled="loading" @click="closeDialog">取消</el-button>
      <el-button
        type="primary"
        :disabled="loading || !files.length"
        :loading="loading"
        @click="submitFiles"
      >
        上传并建立索引
      </el-button>
    </template>
  </el-dialog>
</template>

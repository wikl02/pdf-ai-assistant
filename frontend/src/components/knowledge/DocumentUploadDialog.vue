<script setup lang="ts">
import { ref, watch } from 'vue'
import { FileUp, X } from '@lucide/vue'

const props = defineProps<{ modelValue: boolean; loading: boolean }>()
const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  submit: [files: File[]]
}>()

const files = ref<File[]>([])
const inputRef = ref<HTMLInputElement>()

watch(
  () => props.modelValue,
  (visible) => {
    if (visible) files.value = []
  },
)

function selectFiles(event: Event) {
  files.value = Array.from((event.target as HTMLInputElement).files || [])
}

function removeFile(index: number) {
  files.value.splice(index, 1)
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
    @update:model-value="emit('update:modelValue', $event)"
  >
    <button class="upload-dropzone" type="button" @click="inputRef?.click()">
      <FileUp :size="28" />
      <strong>选择一个或多个文档</strong>
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

    <div v-if="files.length" class="selected-file-list">
      <div v-for="(file, index) in files" :key="`${file.name}-${file.size}`" class="selected-file-item">
        <div>
          <strong>{{ file.name }}</strong>
          <span>{{ formatSize(file.size) }}</span>
        </div>
        <button class="icon-button" title="移除文件" @click="removeFile(index)">
          <X :size="17" />
        </button>
      </div>
    </div>

    <template #footer>
      <el-button @click="emit('update:modelValue', false)">取消</el-button>
      <el-button
        type="primary"
        :disabled="!files.length"
        :loading="loading"
        @click="emit('submit', files)"
      >
        上传并建立索引
      </el-button>
    </template>
  </el-dialog>
</template>

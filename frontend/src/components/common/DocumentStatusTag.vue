<script setup lang="ts">
import { computed } from 'vue'
import type { DocumentStatus } from '../../types'

const props = defineProps<{ status: DocumentStatus }>()

const statusConfig = computed(() => {
  const config = {
    pending: { label: '等待处理', type: 'info' },
    processing: { label: '处理中', type: 'warning' },
    ready: { label: '可用', type: 'success' },
    failed: { label: '处理失败', type: 'danger' },
  } as const
  return config[props.status]
})
</script>

<template>
  <el-tag :type="statusConfig.type" effect="light" size="small">
    {{ statusConfig.label }}
  </el-tag>
</template>

<script setup lang="ts">
import { FileText, Gauge } from '@lucide/vue'
import type { SourceChunk, SourceMetadata } from '../../types'

defineProps<{ sources: SourceChunk[] }>()

function formatLocation(metadata: SourceMetadata): string {
  const start = metadata.start_line || 1
  const end = metadata.end_line || start
  if (metadata.location_type === 'page_line') {
    return `第 ${metadata.page || 1} 页，第 ${start}-${end} 行`
  }
  if (metadata.location_type === 'paragraph') return `第 ${start} 段`
  if (metadata.location_type === 'row') return `第 ${start} 行`
  if (metadata.location_type === 'sheet_row') {
    return `${metadata.sheet || '工作表'}，第 ${start} 行`
  }
  if (metadata.location_type === 'line') return `第 ${start}-${end} 行`
  return '文档内容'
}
</script>

<template>
  <el-collapse class="source-collapse">
    <el-collapse-item :title="`查看 ${sources.length} 条回答来源`" name="sources">
      <div class="source-list">
        <article v-for="(source, index) in sources" :key="`${source.metadata.chunk_id}-${index}`" class="source-item">
          <header>
            <span class="source-file">
              <FileText :size="16" />
              {{ source.metadata.source_name || '未知文档' }}
            </span>
            <span class="source-score">
              <Gauge :size="15" />
              相似度 {{ Math.round(source.score * 100) }}%
            </span>
          </header>
          <p class="source-location">{{ formatLocation(source.metadata) }}</p>
          <p class="source-excerpt">{{ source.text }}</p>
        </article>
      </div>
    </el-collapse-item>
  </el-collapse>
</template>

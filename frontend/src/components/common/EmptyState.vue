<script setup lang="ts">
import { Inbox } from '@lucide/vue'

defineProps<{
  title: string
  description?: string
}>()
</script>

<template>
  <div class="empty-state">
    <span class="empty-icon"><Inbox :size="24" /></span>
    <strong>{{ title }}</strong>
    <p v-if="description">{{ description }}</p>
    <slot />
  </div>
</template>

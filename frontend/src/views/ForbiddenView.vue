<script setup lang="ts">
import { ArrowLeft, ShieldX } from '@lucide/vue'
import { useRouter } from 'vue-router'

import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()

function goBack() {
  router.replace(auth.isAdmin ? '/admin/dashboard' : '/app/chat')
}
</script>

<template>
  <main class="status-page">
    <span class="status-page-icon"><ShieldX :size="34" /></span>
    <h1>无权访问此页面</h1>
    <p>当前账号没有执行此操作所需的管理员权限。</p>
    <el-button type="primary" @click="goBack">
      <ArrowLeft :size="17" />
      返回可访问页面
    </el-button>
  </main>
</template>

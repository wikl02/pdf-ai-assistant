<script setup lang="ts">
import { BookOpen, ChevronDown, LayoutDashboard, LogOut } from '@lucide/vue'
import { useRouter } from 'vue-router'

import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()

function logout() {
  auth.logout()
  router.replace('/login')
}
</script>

<template>
  <div class="chat-layout">
    <header class="chat-topbar">
      <div class="chat-brand">
        <span class="brand-mark"><BookOpen :size="19" /></span>
        <div>
          <strong>企业知识库</strong>
          <small>智能查询工作台</small>
        </div>
      </div>
      <el-dropdown trigger="click">
        <button class="user-menu-button compact">
          <span class="user-avatar">{{ auth.user?.display_name?.[0] || auth.user?.username[0] }}</span>
          <span class="user-menu-copy">
            <strong>{{ auth.user?.display_name || auth.user?.username }}</strong>
            <small>{{ auth.isAdmin ? '管理员' : '普通用户' }}</small>
          </span>
          <ChevronDown :size="16" />
        </button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item v-if="auth.isAdmin" @click="router.push('/admin/dashboard')">
              <LayoutDashboard :size="16" />
              管理后台
            </el-dropdown-item>
            <el-dropdown-item :divided="auth.isAdmin" @click="logout">
              <LogOut :size="16" />
              退出登录
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </header>
    <main class="chat-main">
      <RouterView />
    </main>
  </div>
</template>

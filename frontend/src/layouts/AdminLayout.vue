<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  BookOpen,
  ChevronDown,
  LayoutDashboard,
  LogOut,
  Menu,
  MessageSquareText,
  ShieldCheck,
  Users,
  X,
} from '@lucide/vue'

import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const mobileNavigationOpen = ref(false)

const activeMenu = computed(() => {
  if (route.path.startsWith('/admin/knowledge-bases')) return '/admin/knowledge-bases'
  return route.path
})

function navigate(path: string) {
  mobileNavigationOpen.value = false
  router.push(path)
}

function logout() {
  auth.logout()
  router.replace('/login')
}
</script>

<template>
  <div class="admin-shell">
    <div v-if="mobileNavigationOpen" class="nav-scrim" @click="mobileNavigationOpen = false" />
    <aside :class="['admin-sidebar', { 'is-open': mobileNavigationOpen }]">
      <div class="brand-block">
        <div class="brand-mark"><BookOpen :size="20" /></div>
        <div>
          <strong>企业知识库</strong>
          <span>管理控制台</span>
        </div>
        <button class="icon-button mobile-close" title="关闭导航" @click="mobileNavigationOpen = false">
          <X :size="20" />
        </button>
      </div>

      <el-menu :default-active="activeMenu" class="admin-menu" @select="navigate">
        <el-menu-item index="/admin/dashboard">
          <LayoutDashboard :size="18" />
          <span>仪表盘</span>
        </el-menu-item>
        <el-menu-item index="/admin/knowledge-bases">
          <BookOpen :size="18" />
          <span>知识库管理</span>
        </el-menu-item>
        <el-menu-item index="/admin/users">
          <Users :size="18" />
          <span>用户管理</span>
        </el-menu-item>
        <el-menu-item index="/app/chat">
          <MessageSquareText :size="18" />
          <span>知识查询</span>
        </el-menu-item>
      </el-menu>

      <div class="sidebar-footnote">
        <ShieldCheck :size="17" />
        <span>管理员工作区</span>
      </div>
    </aside>

    <section class="admin-workspace">
      <header class="admin-topbar">
        <button class="icon-button mobile-menu" title="打开导航" @click="mobileNavigationOpen = true">
          <Menu :size="21" />
        </button>
        <div class="topbar-title">
          <span>管理后台</span>
          <strong>{{ route.meta.title }}</strong>
        </div>
        <el-dropdown trigger="click">
          <button class="user-menu-button">
            <span class="user-avatar">{{ auth.user?.display_name?.[0] || auth.user?.username[0] }}</span>
            <span class="user-menu-copy">
              <strong>{{ auth.user?.display_name || auth.user?.username }}</strong>
              <small>管理员</small>
            </span>
            <ChevronDown :size="16" />
          </button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="router.push('/app/chat')">
                <MessageSquareText :size="16" />
                进入知识查询
              </el-dropdown-item>
              <el-dropdown-item divided @click="logout">
                <LogOut :size="16" />
                退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </header>
      <main class="admin-content">
        <RouterView />
      </main>
    </section>
  </div>
</template>

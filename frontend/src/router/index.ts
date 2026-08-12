import { createRouter, createWebHistory } from 'vue-router'

import { useAuthStore } from '../stores/auth'

declare module 'vue-router' {
  interface RouteMeta {
    requiresAuth?: boolean
    adminOnly?: boolean
    title?: string
  }
}

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/login',
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginView.vue'),
      meta: { title: '登录' },
    },
    {
      path: '/admin',
      component: () => import('../layouts/AdminLayout.vue'),
      meta: { requiresAuth: true, adminOnly: true },
      children: [
        {
          path: 'dashboard',
          name: 'admin-dashboard',
          component: () => import('../views/admin/DashboardView.vue'),
          meta: { requiresAuth: true, adminOnly: true, title: '仪表盘' },
        },
        {
          path: 'knowledge-bases',
          name: 'admin-knowledge-bases',
          component: () => import('../views/admin/KnowledgeBasesView.vue'),
          meta: { requiresAuth: true, adminOnly: true, title: '知识库管理' },
        },
        {
          path: 'knowledge-bases/:id',
          name: 'admin-knowledge-base-detail',
          component: () => import('../views/admin/KnowledgeBaseDetailView.vue'),
          meta: { requiresAuth: true, adminOnly: true, title: '知识库详情' },
        },
        {
          path: 'users',
          name: 'admin-users',
          component: () => import('../views/admin/UsersView.vue'),
          meta: { requiresAuth: true, adminOnly: true, title: '用户管理' },
        },
        {
          path: 'audit-logs',
          name: 'admin-audit-logs',
          component: () => import('../views/admin/AuditLogsView.vue'),
          meta: { requiresAuth: true, adminOnly: true, title: '审计日志' },
        },
        {
          path: 'evaluations',
          name: 'admin-evaluations',
          component: () => import('../views/admin/EvaluationsView.vue'),
          meta: { requiresAuth: true, adminOnly: true, title: '质量评估' },
        },
      ],
    },
    {
      path: '/app',
      component: () => import('../layouts/ChatLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        {
          path: 'chat',
          name: 'app-chat',
          component: () => import('../views/chat/ChatView.vue'),
          meta: { requiresAuth: true, title: '知识查询' },
        },
      ],
    },
    {
      path: '/403',
      name: 'forbidden',
      component: () => import('../views/ForbiddenView.vue'),
      meta: { title: '无权访问' },
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/login',
    },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()

  // 已登录用户访问登录页时，按角色送回各自的工作区。
  if (to.name === 'login' && auth.token) {
    try {
      if (!auth.user) await auth.fetchCurrentUser()
      return auth.isAdmin ? '/admin/dashboard' : '/app/chat'
    } catch {
      return true
    }
  }

  if (!to.meta.requiresAuth) return true
  if (!auth.token) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  // 页面刷新时 Pinia 内存状态为空，需要先用本地 token 恢复当前用户。
  if (!auth.user) {
    try {
      await auth.fetchCurrentUser()
    } catch {
      return { name: 'login', query: { redirect: to.fullPath } }
    }
  }

  // 前端守卫负责用户体验；真正的安全边界仍由 FastAPI 的角色依赖保证。
  if (to.meta.adminOnly && !auth.isAdmin) {
    return { name: 'forbidden' }
  }
  return true
})

router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} - 企业知识库` : '企业知识库'
})

export default router

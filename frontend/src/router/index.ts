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

  if (!auth.user) {
    try {
      await auth.fetchCurrentUser()
    } catch {
      return { name: 'login', query: { redirect: to.fullPath } }
    }
  }

  if (to.meta.adminOnly && !auth.isAdmin) {
    return { name: 'forbidden' }
  }
  return true
})

router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} - 企业知识库` : '企业知识库'
})

export default router

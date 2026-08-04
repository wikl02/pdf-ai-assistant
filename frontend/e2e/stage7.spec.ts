import { expect, test, type Page, type Route } from '@playwright/test'
import fs from 'node:fs'
import path from 'node:path'

const screenshotDir = path.resolve('../tmp/screenshots/stage7')
const now = '2026-08-04T09:30:00Z'

const users = {
  super_admin: {
    id: 1,
    username: 'root_admin',
    display_name: '超级管理员',
    role: 'super_admin',
    is_active: true,
    created_at: now,
    updated_at: now,
    last_login_at: now,
    deleted_at: null,
    deleted_by_id: null,
  },
  admin: {
    id: 2,
    username: 'admin',
    display_name: '系统管理员',
    role: 'admin',
    is_active: true,
    created_at: now,
    updated_at: now,
    last_login_at: now,
    deleted_at: null,
    deleted_by_id: null,
  },
  user: {
    id: 2,
    username: 'knowledge_user',
    display_name: '知识查询用户',
    role: 'user',
    is_active: true,
    created_at: now,
    updated_at: now,
    last_login_at: now,
    deleted_at: null,
    deleted_by_id: null,
  },
}

const knowledgeBase = {
  id: 7,
  name: '产品与交付知识库',
  description: '产品制度、FAQ 与项目交付规范',
  collection_name: 'enterprise_kb_7',
  created_by_id: 1,
  document_count: 12,
  chunk_count: 168,
  created_at: now,
  updated_at: now,
}

function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({
    status,
    contentType: 'application/json; charset=utf-8',
    body: JSON.stringify(body),
  })
}

async function mockApi(page: Page, role: 'super_admin' | 'admin' | 'user') {
  page.on('pageerror', (error) => console.error(`Browser page error: ${error.message}`))
  page.on('console', (message) => {
    if (message.type() === 'error') console.error(`Browser console error: ${message.text()}`)
  })
  await page.addInitScript(() => {
    localStorage.setItem('enterprise_kb_access_token', 'stage7-e2e-token')
  })

  await page.route(/^http:\/\/127\.0\.0\.1:800[01]\/api\//, async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    const pathname = url.pathname

    if (pathname === '/api/auth/me') return json(route, users[role])
    if (pathname === '/api/admin/users' && request.method() === 'GET') {
      return json(route, [
        users.super_admin,
        users.admin,
        users.user,
        {
          ...users.user,
          id: 4,
          username: 'former_user',
          display_name: '已离职用户',
          is_active: false,
          deleted_at: now,
          deleted_by_id: 1,
        },
      ])
    }
    if (pathname === '/api/knowledge-bases') return json(route, [knowledgeBase])
    if (pathname === '/api/admin/knowledge-bases/7') {
      return json(route, {
        ...knowledgeBase,
        documents: [{
          id: 21,
          filename: '客服工单规范.docx',
          file_type: 'docx',
          file_size: 48320,
          sha256: 'test-sha256',
          storage_path: '/app/data/uploads/test.docx',
          status: 'ready',
          chunk_count: 18,
          error_message: null,
          current_version_number: 2,
          uploaded_by_id: 1,
          created_at: now,
          updated_at: now,
        }],
      })
    }
    if (pathname === '/api/admin/knowledge-bases/7/documents/21/lifecycle') {
      return json(route, {
        document: {
          id: 21, filename: '客服工单规范.docx', file_type: 'docx', file_size: 48320,
          sha256: 'test-sha256', storage_path: '/app/data/uploads/test.docx', status: 'ready',
          chunk_count: 18, error_message: null, current_version_number: 2, uploaded_by_id: 1,
          created_at: now, updated_at: now,
        },
        versions: [
          { id: 2, document_id: 21, version_number: 2, filename: '客服工单规范.docx', file_type: 'docx', file_size: 48320, sha256: 'v2', status: 'ready', chunk_count: 18, error_message: null, created_by_id: 1, created_at: now },
          { id: 1, document_id: 21, version_number: 1, filename: '客服工单规范.docx', file_type: 'docx', file_size: 42100, sha256: 'v1', status: 'ready', chunk_count: 15, error_message: null, created_by_id: 1, created_at: '2026-08-01T09:30:00Z' },
        ],
        index_tasks: [
          { id: 3, document_id: 21, knowledge_base_id: 7, version_number: 2, trigger: 'version_upload', status: 'succeeded', chunk_count: 18, error_message: null, duration_ms: 1840, initiated_by_id: 1, started_at: now, completed_at: now, created_at: now },
          { id: 2, document_id: 21, knowledge_base_id: 7, version_number: 1, trigger: 'reindex', status: 'failed', chunk_count: 0, error_message: 'Embedding 服务连接超时', duration_ms: 30120, initiated_by_id: 1, started_at: now, completed_at: now, created_at: now },
          { id: 1, document_id: 21, knowledge_base_id: 7, version_number: 1, trigger: 'upload', status: 'succeeded', chunk_count: 15, error_message: null, duration_ms: 1520, initiated_by_id: 1, started_at: now, completed_at: now, created_at: now },
        ],
      })
    }
    if (pathname === '/api/chat/conversations' && request.method() === 'GET') {
      return json(route, [
        {
          id: 31,
          user_id: 2,
          knowledge_base_id: knowledgeBase.id,
          knowledge_base_name: knowledgeBase.name,
          title: '售后响应时限是多少',
          message_count: 2,
          created_at: now,
          updated_at: now,
        },
        {
          id: 30,
          user_id: 2,
          knowledge_base_id: knowledgeBase.id,
          knowledge_base_name: knowledgeBase.name,
          title: '项目上线前需要哪些检查',
          message_count: 4,
          created_at: '2026-08-03T08:20:00Z',
          updated_at: '2026-08-03T08:28:00Z',
        },
      ])
    }
    if (pathname === '/api/chat/conversations/31') {
      return json(route, {
        id: 31,
        user_id: 2,
        knowledge_base_id: knowledgeBase.id,
        knowledge_base_name: knowledgeBase.name,
        title: '售后响应时限是多少',
        message_count: 2,
        created_at: now,
        updated_at: now,
        messages: [
          {
            id: 101,
            conversation_id: 31,
            role: 'user',
            content: '售后工单需要在多久内首次响应？',
            sources: null,
            status: 'complete',
            response_time_ms: null,
            created_at: now,
          },
          {
            id: 102,
            conversation_id: 31,
            role: 'assistant',
            content: '普通工单应在 4 小时内首次响应，紧急工单应在 30 分钟内响应。',
            sources: [
              {
                text: '普通工单首次响应时间不超过 4 小时；紧急工单不超过 30 分钟。',
                score: 0.92,
                metadata: {
                  source_name: '客服工单规范.docx',
                  location_type: 'line',
                  start_line: 18,
                  end_line: 20,
                },
              },
            ],
            status: 'complete',
            response_time_ms: 860,
            created_at: now,
          },
        ],
      })
    }
    if (pathname === '/api/admin/audit-logs/summary') {
      return json(route, {
        audit_event_count: 286,
        question_count: 143,
        failed_event_count: 6,
        active_user_count: 18,
        conversation_count: 79,
        message_count: 314,
      })
    }
    if (pathname === '/api/admin/audit-logs') {
      return json(route, {
        total: 3,
        page: 1,
        page_size: 30,
        items: [
          {
            id: 3,
            event: 'question_answered',
            outcome: 'success',
            actor_id: 2,
            actor_name: 'knowledge_user',
            client_ip: '10.0.0.28',
            details: { knowledge_base_id: 7, source_count: 3, response_time_ms: 860 },
            created_at: now,
          },
          {
            id: 2,
            event: 'documents_uploaded',
            outcome: 'success',
            actor_id: 1,
            actor_name: 'admin',
            client_ip: '10.0.0.12',
            details: { file_count: 2, chunk_count: 24 },
            created_at: '2026-08-04T08:40:00Z',
          },
          {
            id: 1,
            event: 'login',
            outcome: 'failed',
            actor_id: null,
            actor_name: 'unknown_user',
            client_ip: '10.0.0.99',
            details: { reason: 'invalid_credentials' },
            created_at: '2026-08-04T08:10:00Z',
          },
        ],
      })
    }

    return json(route, { detail: `Unhandled mock API: ${request.method()} ${pathname}` }, 501)
  })
}

test.beforeAll(() => fs.mkdirSync(screenshotDir, { recursive: true }))

test('用户可以恢复历史问答并查看引用来源', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await mockApi(page, 'user')
  await page.goto('/app/chat')

  await expect(page.getByText('产品与交付知识库').first()).toBeVisible()
  await page.getByText('售后响应时限是多少').click()
  await expect(page.getByText('普通工单应在 4 小时内首次响应')).toBeVisible()
  await page.getByText('查看 1 条回答来源').click()
  await expect(page.getByText('客服工单规范.docx')).toBeVisible()
  await page.screenshot({ path: path.join(screenshotDir, 'chat-history-1440.png'), fullPage: true })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy()

  await page.setViewportSize({ width: 390, height: 844 })
  await expect(page.getByText('售后响应时限是多少')).toBeVisible()
  await page.screenshot({ path: path.join(screenshotDir, 'chat-history-390.png'), fullPage: true })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy()
})

test('管理员可以查看审计概况和关键操作记录', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await mockApi(page, 'admin')
  await page.goto('/admin/audit-logs')

  await expect(page.getByRole('heading', { name: '审计日志' })).toBeVisible()
  await expect(page.getByText('286')).toBeVisible()
  await expect(page.locator('.el-table').getByText('知识问答')).toBeVisible()
  await expect(page.locator('.el-table').getByText('上传文档')).toBeVisible()
  await page.screenshot({ path: path.join(screenshotDir, 'audit-logs-1440.png'), fullPage: true })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy()

  await page.setViewportSize({ width: 390, height: 844 })
  await expect(page.locator('.mobile-menu')).toBeVisible()
  await expect(page.locator('.admin-sidebar')).not.toBeInViewport()
  await page.screenshot({ path: path.join(screenshotDir, 'audit-logs-390.png'), fullPage: true })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy()
})

test('超级管理员可以区分用户层级并恢复软删除账号', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await mockApi(page, 'super_admin')
  await page.goto('/admin/users')

  await expect(page.getByRole('heading', { name: '用户管理' })).toBeVisible()
  await expect(page.getByText('超级管理员').first()).toBeVisible()
  await expect(page.getByText('已离职用户')).toBeVisible()
  await expect(page.getByRole('button', { name: '恢复' })).toBeVisible()
  await page.screenshot({ path: path.join(screenshotDir, 'users-super-admin-1440.png'), fullPage: true })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy()
})

test('管理员可以查看文档版本和索引失败原因', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await mockApi(page, 'admin')
  await page.goto('/admin/knowledge-bases/7')

  await page.getByRole('button', { name: '生命周期' }).click()
  await expect(page.getByText('文档生命周期')).toBeVisible()
  await expect(page.getByText('V2').first()).toBeVisible()
  await expect(page.getByText('Embedding 服务连接超时')).toBeVisible()
  await page.waitForTimeout(300)
  await page.screenshot({ path: path.join(screenshotDir, 'document-lifecycle-1440.png'), fullPage: true })

  await page.setViewportSize({ width: 390, height: 844 })
  await expect(page.getByText('文档生命周期')).toBeVisible()
  await page.waitForTimeout(300)
  await page.screenshot({ path: path.join(screenshotDir, 'document-lifecycle-390.png'), fullPage: true })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy()
})

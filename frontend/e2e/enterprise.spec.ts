import { expect, test } from '@playwright/test'
import fs from 'node:fs'
import path from 'node:path'

const adminUsername = process.env.E2E_ADMIN_USERNAME || ''
const adminPassword = process.env.E2E_ADMIN_PASSWORD || ''
const normalUsername = `frontend_e2e_${Date.now()}`
const initialPassword = 'FrontendE2E123!'
const resetPassword = 'FrontendChanged123!'
const knowledgeBaseName = `前端验收知识库 ${Date.now()}`
const screenshotDir = path.resolve('../tmp/screenshots')
const sampleDirectory = path.resolve('../sample_documents')
const sampleFile = path.join(
  sampleDirectory,
  fs.readdirSync(sampleDirectory).find((name) => name.endsWith('.txt')) || '',
)

let knowledgeBaseId = 0
let documentId = 0
let adminToken = ''

async function login(page, username: string, password: string) {
  await page.goto('/login')
  await page.getByLabel('用户名').fill(username)
  await page.getByLabel('密码').fill(password)
  await page.getByRole('button', { name: '登录', exact: true }).click()
}

test.describe.serial('企业知识库正式前端', () => {
  test.beforeAll(async ({ request }) => {
    fs.mkdirSync(screenshotDir, { recursive: true })
    expect(adminUsername).toBeTruthy()
    expect(adminPassword).toBeTruthy()
    const response = await request.post('http://127.0.0.1:8001/api/auth/login', {
      data: { username: adminUsername, password: adminPassword },
    })
    expect(response.ok()).toBeTruthy()
    adminToken = (await response.json()).access_token
  })

  test.afterAll(async ({ request }) => {
    if (knowledgeBaseId && documentId) {
      await request.delete(
        `http://127.0.0.1:8001/api/admin/knowledge-bases/${knowledgeBaseId}/documents/${documentId}`,
        { headers: { Authorization: `Bearer ${adminToken}` } },
      )
    }
  })

  test('管理员完成知识库、文档和用户管理', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 })
    await login(page, adminUsername, adminPassword)
    await expect(page).toHaveURL(/\/admin\/dashboard$/)
    await expect(page.getByRole('heading', { name: '仪表盘' })).toBeVisible()
    await page.screenshot({ path: path.join(screenshotDir, 'admin-dashboard-1440.png'), fullPage: true })
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy()

    await page.getByRole('menuitem', { name: '知识库管理' }).click()
    await page.getByRole('button', { name: '创建知识库' }).first().click()
    await page.getByLabel('知识库名称').fill(knowledgeBaseName)
    await page.getByLabel('说明').fill('用于验证 Vue 企业前端的临时知识库')
    const createResponsePromise = page.waitForResponse(
      (response) => response.url().endsWith('/api/admin/knowledge-bases') && response.request().method() === 'POST',
    )
    await page.getByRole('button', { name: '创建', exact: true }).click()
    const createResponse = await createResponsePromise
    expect(createResponse.status()).toBe(201)
    knowledgeBaseId = (await createResponse.json()).id
    await expect(page).toHaveURL(new RegExp(`/admin/knowledge-bases/${knowledgeBaseId}$`))

    await page.getByRole('button', { name: '上传文档' }).first().click()
    await page.locator('input[type="file"]').setInputFiles(sampleFile)
    const uploadResponsePromise = page.waitForResponse(
      (response) => response.url().includes(`/knowledge-bases/${knowledgeBaseId}/documents`) && response.request().method() === 'POST',
    )
    await page.getByRole('button', { name: '上传并建立索引' }).click()
    const uploadResponse = await uploadResponsePromise
    expect(uploadResponse.status()).toBe(201)
    documentId = (await uploadResponse.json()).documents[0].id
    await expect(page.locator('tbody').getByText(path.basename(sampleFile))).toBeVisible()

    await page.setViewportSize({ width: 1024, height: 768 })
    await page.screenshot({ path: path.join(screenshotDir, 'knowledge-detail-1024.png'), fullPage: true })
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy()

    const reindexResponsePromise = page.waitForResponse(
      (response) => response.url().endsWith(`/documents/${documentId}/reindex`),
    )
    await page.getByRole('button', { name: '重新索引' }).click()
    expect((await reindexResponsePromise).status()).toBe(200)

    await page.getByRole('menuitem', { name: '用户管理' }).click()
    await page.getByRole('button', { name: '创建账号' }).click()
    await page.getByLabel('用户名').fill(normalUsername)
    await page.getByLabel('显示名称').fill('前端验收用户')
    await page.getByLabel('初始密码').fill(initialPassword)
    const createUserResponsePromise = page.waitForResponse(
      (response) => response.url().endsWith('/api/admin/users') && response.request().method() === 'POST',
    )
    await page.getByLabel('创建用户').getByRole('button', { name: '创建账号', exact: true }).click()
    expect((await createUserResponsePromise).status()).toBe(201)
    const userRow = page.getByRole('row').filter({ hasText: normalUsername })
    await expect(userRow).toBeVisible()

    await userRow.locator('.el-select').click()
    const roleAdminResponse = page.waitForResponse(
      (response) => response.url().includes('/role') && response.request().method() === 'PATCH',
    )
    await page.getByRole('option', { name: '管理员' }).click()
    expect((await roleAdminResponse).status()).toBe(200)

    const refreshedUserRow = page.getByRole('row').filter({ hasText: normalUsername })
    await refreshedUserRow.locator('.el-select').click()
    const roleUserResponse = page.waitForResponse(
      (response) => response.url().includes('/role') && response.request().method() === 'PATCH',
    )
    await page.getByRole('option', { name: '普通用户' }).click()
    expect((await roleUserResponse).status()).toBe(200)

    const currentRow = page.getByRole('row').filter({ hasText: normalUsername })
    const disableResponse = page.waitForResponse(
      (response) => response.url().includes('/status') && response.request().method() === 'PATCH',
    )
    await currentRow.locator('.el-switch').click()
    expect((await disableResponse).status()).toBe(200)
    const enableResponse = page.waitForResponse(
      (response) => response.url().includes('/status') && response.request().method() === 'PATCH',
    )
    await page.getByRole('row').filter({ hasText: normalUsername }).locator('.el-switch').click()
    expect((await enableResponse).status()).toBe(200)

    await page.getByRole('row').filter({ hasText: normalUsername }).getByRole('button', { name: '重置密码' }).click()
    await page.locator('.el-message-box input').fill(resetPassword)
    const resetResponse = page.waitForResponse(
      (response) => response.url().includes('/reset-password') && response.request().method() === 'POST',
    )
    await page.getByRole('button', { name: '确认重置' }).click()
    expect((await resetResponse).status()).toBe(200)
    await page.setViewportSize({ width: 1440, height: 900 })
    await page.screenshot({ path: path.join(screenshotDir, 'user-management-1440.png'), fullPage: true })
  })

  test('普通用户进入查询页且越权显示 403', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 })
    await login(page, normalUsername, resetPassword)
    await expect(page).toHaveURL(/\/app\/chat$/)
    const knowledgeBaseButton = page.getByRole('button', { name: new RegExp(knowledgeBaseName) })
    await expect(knowledgeBaseButton).toBeVisible()
    await knowledgeBaseButton.click()
    await page.screenshot({ path: path.join(screenshotDir, 'chat-desktop-1440.png'), fullPage: true })
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy()

    await page.getByPlaceholder('输入需要查询的问题').fill('火星量子引力股票预测')
    const askResponsePromise = page.waitForResponse(
      (response) => response.url().endsWith('/api/chat/ask') && response.request().method() === 'POST',
    )
    await page.getByRole('button', { name: '发送' }).click()
    expect((await askResponsePromise).status()).toBe(200)
    await expect(page.getByText('正在检索知识库')).toBeHidden({ timeout: 180_000 })
    await expect(page.getByText('知识库助手')).toBeVisible()

    await page.goto('/admin/dashboard')
    await expect(page).toHaveURL(/\/403$/)
    await expect(page.getByRole('heading', { name: '无权访问此页面' })).toBeVisible()

    await page.setViewportSize({ width: 390, height: 844 })
    await page.goto('/app/chat')
    await expect(page).toHaveURL(/\/app\/chat$/)
    await page.screenshot({ path: path.join(screenshotDir, 'chat-mobile-390.png'), fullPage: true })
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy()
  })
})

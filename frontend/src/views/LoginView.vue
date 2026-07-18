<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { BookOpen, LockKeyhole, UserRound } from '@lucide/vue'
import type { FormInstance, FormRules } from 'element-plus'

import { getErrorMessage } from '../api/http'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const formRef = ref<FormInstance>()
const loading = ref(false)
const errorMessage = ref('')
const form = reactive({ username: '', password: '' })
const rules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function submit() {
  if (!(await formRef.value?.validate())) return
  loading.value = true
  errorMessage.value = ''
  try {
    const user = await auth.login(form.username.trim(), form.password)
    const requestedPath = typeof route.query.redirect === 'string' ? route.query.redirect : ''
    if (requestedPath) {
      await router.replace(requestedPath)
    } else {
      await router.replace(user?.role === 'admin' ? '/admin/dashboard' : '/app/chat')
    }
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '登录失败，请检查用户名和密码')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="login-page">
    <section class="login-brand-panel">
      <div class="login-brand-lockup">
        <span class="brand-mark large"><BookOpen :size="24" /></span>
        <div>
          <strong>企业知识库</strong>
          <span>Enterprise Knowledge Workspace</span>
        </div>
      </div>
      <div class="login-context">
        <h1>内部知识统一管理与查询</h1>
        <p>集中维护企业文档，使用可信来源快速完成知识检索与问答。</p>
      </div>
      <small>仅限授权账号访问</small>
    </section>

    <section class="login-form-panel">
      <div class="login-form-wrap">
        <div class="mobile-login-brand">
          <span class="brand-mark"><BookOpen :size="20" /></span>
          <strong>企业知识库</strong>
        </div>
        <div class="login-heading">
          <h2>登录工作台</h2>
          <p>使用企业账号继续</p>
        </div>
        <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon :closable="false" />
        <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="submit">
          <el-form-item label="用户名" prop="username">
            <el-input v-model="form.username" size="large" autocomplete="username" placeholder="请输入用户名">
              <template #prefix><UserRound :size="18" /></template>
            </el-input>
          </el-form-item>
          <el-form-item label="密码" prop="password">
            <el-input
              v-model="form.password"
              size="large"
              type="password"
              autocomplete="current-password"
              show-password
              placeholder="请输入密码"
              @keyup.enter="submit"
            >
              <template #prefix><LockKeyhole :size="18" /></template>
            </el-input>
          </el-form-item>
          <el-button class="login-submit" type="primary" size="large" :loading="loading" @click="submit">
            登录
          </el-button>
        </el-form>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { KeyRound, Plus, RefreshCw, RotateCcw, ShieldCheck, Trash2 } from '@lucide/vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'

import { getErrorMessage } from '../../api/http'
import {
  createUserApi,
  deleteUserApi,
  listUsersApi,
  resetUserPasswordApi,
  restoreUserApi,
  updateUserRoleApi,
  updateUserStatusApi,
} from '../../api/users'
import EmptyState from '../../components/common/EmptyState.vue'
import PageHeader from '../../components/common/PageHeader.vue'
import { useAuthStore } from '../../stores/auth'
import type { User, UserRole } from '../../types'

const auth = useAuthStore()
const users = ref<User[]>([])
const loading = ref(true)
const errorMessage = ref('')
const dialogOpen = ref(false)
const creating = ref(false)
const updatingUserId = ref<number | null>(null)
const formRef = ref<FormInstance>()
const form = reactive({ username: '', displayName: '', password: '', role: 'user' as UserRole })
const rules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { pattern: /^[A-Za-z0-9_.-]+$/, message: '只能使用字母、数字、点、下划线和横线', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入初始密码', trigger: 'blur' },
    { min: 8, message: '密码至少 8 个字符', trigger: 'blur' },
  ],
}

const roleLabels: Record<UserRole, string> = {
  super_admin: '超级管理员',
  admin: '管理员',
  user: '普通用户',
}

function canManage(user: User) {
  if (user.id === auth.user?.id || user.deleted_at) return false
  return auth.isSuperAdmin || user.role === 'user'
}

function canChangeRole(user: User) {
  return auth.isSuperAdmin && user.id !== auth.user?.id && !user.deleted_at
}

function canResetPassword(user: User) {
  return !user.deleted_at && (auth.isSuperAdmin || user.role === 'user')
}

function userRowClassName({ row }: { row: User }) {
  return row.deleted_at ? 'is-deleted-row' : ''
}

async function loadUsers() {
  loading.value = true
  errorMessage.value = ''
  try {
    users.value = await listUsersApi()
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '用户列表加载失败')
  } finally {
    loading.value = false
  }
}

function openCreateDialog() {
  Object.assign(form, { username: '', displayName: '', password: '', role: 'user' })
  formRef.value?.clearValidate()
  dialogOpen.value = true
}

async function createUser() {
  if (!(await formRef.value?.validate())) return
  creating.value = true
  try {
    await createUserApi({
      username: form.username.trim(),
      password: form.password,
      display_name: form.displayName.trim() || undefined,
      role: form.role,
    })
    ElMessage.success('用户创建成功')
    dialogOpen.value = false
    await loadUsers()
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '用户创建失败'))
  } finally {
    creating.value = false
  }
}

async function changeStatus(user: User, value: string | number | boolean) {
  updatingUserId.value = user.id
  try {
    await updateUserStatusApi(user.id, Boolean(value))
    ElMessage.success(Boolean(value) ? '用户已启用' : '用户已禁用')
    await loadUsers()
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '用户状态修改失败'))
    await loadUsers()
  } finally {
    updatingUserId.value = null
  }
}

async function changeRole(user: User, role: UserRole) {
  updatingUserId.value = user.id
  try {
    await updateUserRoleApi(user.id, role)
    ElMessage.success('用户角色已更新')
    await loadUsers()
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '角色修改失败'))
    await loadUsers()
  } finally {
    updatingUserId.value = null
  }
}

async function resetPassword(user: User) {
  try {
    const { value } = await ElMessageBox.prompt(
      `为用户“${user.username}”设置新密码。`,
      '重置密码',
      {
        confirmButtonText: '确认重置',
        cancelButtonText: '取消',
        inputType: 'password',
        inputPattern: /^.{8,72}$/,
        inputErrorMessage: '密码长度应为 8-72 个字符',
      },
    )
    updatingUserId.value = user.id
    await resetUserPasswordApi(user.id, value)
    ElMessage.success('密码已重置')
  } catch (error) {
    if (error === 'cancel' || error === 'close') return
    ElMessage.error(getErrorMessage(error, '密码重置失败'))
  } finally {
    updatingUserId.value = null
  }
}

async function deleteUser(user: User) {
  try {
    await ElMessageBox.confirm(
      `确定删除账号“${user.username}”吗？账号将无法登录，但其文档、问答和审计记录会被保留。`,
      '删除用户',
      { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消' },
    )
    updatingUserId.value = user.id
    await deleteUserApi(user.id)
    ElMessage.success('用户已删除，可由有权限的管理员恢复')
    await loadUsers()
  } catch (error) {
    if (error === 'cancel' || error === 'close') return
    ElMessage.error(getErrorMessage(error, '用户删除失败'))
  } finally {
    updatingUserId.value = null
  }
}

async function restoreUser(user: User) {
  try {
    await ElMessageBox.confirm(
      `恢复账号“${user.username}”并允许其重新登录吗？`,
      '恢复用户',
      { confirmButtonText: '确认恢复', cancelButtonText: '取消' },
    )
    updatingUserId.value = user.id
    await restoreUserApi(user.id)
    ElMessage.success('用户已恢复')
    await loadUsers()
  } catch (error) {
    if (error === 'cancel' || error === 'close') return
    ElMessage.error(getErrorMessage(error, '用户恢复失败'))
  } finally {
    updatingUserId.value = null
  }
}

onMounted(loadUsers)
</script>

<template>
  <section>
    <PageHeader title="用户管理" description="管理系统账号、状态和角色权限。">
      <template #actions>
        <el-button :loading="loading" @click="loadUsers">
          <RefreshCw :size="16" />
          刷新
        </el-button>
        <el-button type="primary" @click="openCreateDialog">
          <Plus :size="17" />
          创建账号
        </el-button>
      </template>
    </PageHeader>

    <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon @close="errorMessage = ''" />

    <section v-loading="loading" class="content-section table-section">
      <el-table v-if="users.length" :data="users" size="small" row-key="id" :row-class-name="userRowClassName">
        <el-table-column label="用户" min-width="210">
          <template #default="scope">
            <div class="user-table-cell">
              <span class="user-avatar small">{{ scope.row.display_name?.[0] || scope.row.username[0] }}</span>
              <div class="primary-cell">
                <strong>{{ scope.row.display_name || scope.row.username }}</strong>
                <span>{{ scope.row.username }}<template v-if="scope.row.deleted_at"> · 已删除</template></span>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="角色" width="150">
          <template #default="scope">
            <el-select v-if="canChangeRole(scope.row)"
              :model-value="scope.row.role"
              size="small"
              :disabled="updatingUserId === scope.row.id"
              @change="changeRole(scope.row, $event)"
            >
              <el-option label="超级管理员" value="super_admin" />
              <el-option label="管理员" value="admin" />
              <el-option label="普通用户" value="user" />
            </el-select>
            <el-tag v-else :type="scope.row.role === 'super_admin' ? 'danger' : scope.row.role === 'admin' ? 'warning' : 'info'" size="small">
              <ShieldCheck v-if="scope.row.role === 'super_admin'" :size="13" />
              {{ roleLabels[scope.row.role as UserRole] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="scope">
            <el-tag v-if="scope.row.deleted_at" type="info" size="small">已删除</el-tag>
            <el-switch v-else
              :model-value="scope.row.is_active"
              :loading="updatingUserId === scope.row.id"
              :disabled="!canManage(scope.row)"
              @change="changeStatus(scope.row, $event)"
            />
          </template>
        </el-table-column>
        <el-table-column label="最后登录" width="180">
          <template #default="scope">
            {{ scope.row.last_login_at ? new Date(scope.row.last_login_at).toLocaleString('zh-CN') : '尚未登录' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="230" fixed="right">
          <template #default="scope">
            <el-button v-if="canResetPassword(scope.row)" text type="primary" :loading="updatingUserId === scope.row.id" @click="resetPassword(scope.row)">
              <KeyRound :size="15" />
              重置密码
            </el-button>
            <el-button
              v-if="scope.row.deleted_at && (auth.isSuperAdmin || scope.row.role === 'user')"
              text
              type="primary"
              :loading="updatingUserId === scope.row.id"
              @click="restoreUser(scope.row)"
            >
              <RotateCcw :size="15" />
              恢复
            </el-button>
            <el-button
              v-else-if="canManage(scope.row)"
              text
              type="danger"
              :loading="updatingUserId === scope.row.id"
              @click="deleteUser(scope.row)"
            >
              <Trash2 :size="15" />
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <EmptyState v-else-if="!loading" title="暂无用户" description="创建账号后，用户即可登录系统。" />
    </section>

    <el-dialog v-model="dialogOpen" title="创建用户" width="520px" class="responsive-dialog">
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" maxlength="64" placeholder="例如：zhangsan" />
        </el-form-item>
        <el-form-item label="显示名称">
          <el-input v-model="form.displayName" maxlength="100" placeholder="例如：张三" />
        </el-form-item>
        <el-form-item label="初始密码" prop="password">
          <el-input v-model="form.password" type="password" show-password maxlength="72" />
        </el-form-item>
        <el-form-item label="角色">
          <el-radio-group v-model="form.role">
            <el-radio-button value="user">普通用户</el-radio-button>
            <el-radio-button v-if="auth.isSuperAdmin" value="admin">管理员</el-radio-button>
            <el-radio-button v-if="auth.isSuperAdmin" value="super_admin">超级管理员</el-radio-button>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogOpen = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="createUser">创建账号</el-button>
      </template>
    </el-dialog>
  </section>
</template>

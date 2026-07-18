<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'

const props = defineProps<{ modelValue: boolean; loading: boolean }>()
const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  submit: [payload: { name: string; description?: string }]
}>()

const formRef = ref<FormInstance>()
const form = reactive({ name: '', description: '' })
const rules: FormRules = {
  name: [
    { required: true, message: '请输入知识库名称', trigger: 'blur' },
    { max: 120, message: '名称不能超过 120 个字符', trigger: 'blur' },
  ],
}

watch(
  () => props.modelValue,
  (visible) => {
    if (!visible) return
    form.name = ''
    form.description = ''
    formRef.value?.clearValidate()
  },
)

async function submit() {
  if (!(await formRef.value?.validate())) return
  emit('submit', {
    name: form.name.trim(),
    description: form.description.trim() || undefined,
  })
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    title="创建知识库"
    width="520px"
    class="responsive-dialog"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
      <el-form-item label="知识库名称" prop="name">
        <el-input v-model="form.name" maxlength="120" placeholder="例如：产品与客户支持" />
      </el-form-item>
      <el-form-item label="说明">
        <el-input
          v-model="form.description"
          type="textarea"
          :rows="4"
          maxlength="2000"
          show-word-limit
          placeholder="说明该知识库的内容范围和适用人员"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :loading="loading" @click="submit">创建</el-button>
    </template>
  </el-dialog>
</template>

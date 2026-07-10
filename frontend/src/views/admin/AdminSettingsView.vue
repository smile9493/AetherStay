<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api'

interface AutoCheckoutSettings {
  enabled: boolean
  checkout_time: string
  timezone: string
}

const loading = ref(false)
const saving = ref(false)

const form = ref<AutoCheckoutSettings>({
  enabled: true,
  checkout_time: '12:00',
  timezone: 'Asia/Shanghai',
})

onMounted(loadSettings)

async function loadSettings() {
  loading.value = true
  try {
    const { data } = await api.get<AutoCheckoutSettings>('/admin/settings/auto-checkout')
    form.value = data
  } catch {
    ElMessage.error('加载系统设置失败')
  } finally {
    loading.value = false
  }
}

async function saveSettings() {
  saving.value = true
  try {
    const { data } = await api.put<AutoCheckoutSettings>(
      '/admin/settings/auto-checkout',
      form.value,
    )
    form.value = data
    ElMessage.success('自动退房设置已保存')
  } catch (err: any) {
    const msg = err.response?.data?.detail || '保存失败，请检查时间格式'
    ElMessage.error(typeof msg === 'string' ? msg : '保存失败')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div v-loading="loading" class="settings-page">
    <div class="page-header">
      <div>
        <h3>系统设置</h3>
        <p>配置酒店运营相关的自动化策略</p>
      </div>
    </div>

    <el-card class="settings-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span>到点自动退房</span>
          <el-switch v-model="form.enabled" active-text="已启用" inactive-text="已关闭" />
        </div>
      </template>

      <p class="hint">
        仅对<strong>已入住（checked_in）</strong>订单生效。到达退房日当天设定时间后，系统将自动将订单标记为已退房。
        逾期未入住的已付款订单不会自动处理，需管理员在订单调度中人工办理。
      </p>

      <el-form label-position="top" class="settings-form">
        <el-form-item label="退房日触发时间">
          <el-time-picker
            v-model="form.checkout_time"
            format="HH:mm"
            value-format="HH:mm"
            placeholder="选择时间"
            :disabled="!form.enabled"
            style="width: 160px"
          />
          <span class="field-hint">默认 12:00，即退房日中午自动退房</span>
        </el-form-item>

        <el-form-item label="业务时区">
          <el-input v-model="form.timezone" disabled style="width: 240px" />
          <span class="field-hint">当前固定为 Asia/Shanghai（UTC+8）</span>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="saving" @click="saveSettings">
            保存设置
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<style scoped>
.settings-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.page-header h3 {
  font-size: 20px;
  font-weight: 700;
  margin-bottom: 4px;
}

.page-header p {
  font-size: 13px;
  color: var(--text-secondary);
}

.settings-card {
  border: 1px solid var(--card-border);
  border-radius: var(--radius-md);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
}

.hint {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.6;
  margin-bottom: 20px;
}

.settings-form {
  max-width: 480px;
}

.field-hint {
  display: block;
  margin-top: 6px;
  font-size: 12px;
  color: var(--text-muted);
}
</style>

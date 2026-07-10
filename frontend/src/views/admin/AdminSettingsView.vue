<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Timer } from '@element-plus/icons-vue'
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
    ElMessage.error('加载系统设置失败，请确认已执行 003_system_settings 迁移')
  } finally {
    loading.value = false
  }
}

async function saveSettings() {
  if (!form.value.checkout_time) {
    ElMessage.warning('请选择退房触发时间')
    return
  }
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
    <div class="panel-header">
      <div class="header-icon">
        <el-icon><Timer /></el-icon>
      </div>
      <div class="header-info">
        <h3>系统设置</h3>
        <p>配置酒店运营自动化策略，含到点自动退房时间与开关</p>
      </div>
    </div>

    <div class="settings-card glass-panel-inner">
      <div class="card-header">
        <div>
          <h4>到点自动退房</h4>
          <span class="sub">Auto Checkout</span>
        </div>
        <el-switch
          v-model="form.enabled"
          active-text="已启用"
          inactive-text="已关闭"
          inline-prompt
        />
      </div>

      <p class="hint">
        仅对<strong>已入住（checked_in）</strong>订单生效。到达退房日当天设定时间后，系统将自动将订单标记为已退房。
        逾期未入住的已付款订单不会自动处理，需管理员在订单调度中人工办理。
      </p>

      <el-form label-position="top" class="settings-form">
        <el-form-item label="退房日触发时间">
          <el-time-select
            v-model="form.checkout_time"
            start="06:00"
            step="00:30"
            end="23:30"
            placeholder="选择时间"
            :disabled="!form.enabled"
            style="width: 180px"
          />
          <span class="field-hint">例如 12:00 表示退房日中午 12:00 后自动退房</span>
        </el-form-item>

        <el-form-item label="业务时区">
          <el-input v-model="form.timezone" disabled style="width: 240px" />
          <span class="field-hint">当前固定为 Asia/Shanghai（UTC+8）</span>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" class="save-btn" :loading="saving" @click="saveSettings">
            保存设置
          </el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<style scoped>
.settings-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-icon {
  width: 46px;
  height: 46px;
  border-radius: 12px;
  background: var(--primary-light);
  color: var(--primary-color);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.1);
}

.header-info h3 {
  font-size: 20px;
  font-weight: 800;
  color: var(--text-primary);
}

.header-info p {
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: 2px;
}

.settings-card {
  padding: 24px;
  background: rgba(255, 255, 255, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.4);
  border-radius: var(--radius-lg);
  box-shadow: 0 10px 25px -10px rgba(99, 102, 241, 0.04);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(99, 102, 241, 0.1);
}

.card-header h4 {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
}

.card-header .sub {
  font-size: 11px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
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

.save-btn {
  background: var(--accent-gradient);
  border: none;
  font-weight: 600;
}
</style>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api'

const loading = ref(false)

// 日期范围选择
const dateRange = ref<[Date, Date]>([
  new Date(),
  new Date(Date.now() + 13 * 86400000),
])

const rooms = ref<{ id: number; room_number: string; room_type: string }[]>([])
const dates = ref<string[]>([])
const matrix = ref<Record<string, Record<string, string>>>({})

onMounted(loadMatrix)

async function loadMatrix() {
  if (!dateRange.value[0] || !dateRange.value[1]) return
  loading.value = true
  try {
    const start = formatDate(dateRange.value[0])
    const end = formatDate(dateRange.value[1])
    const { data } = await api.get('/admin/inventory', {
      params: { start_date: start, end_date: end },
    })
    rooms.value = data.rooms
    dates.value = data.dates
    matrix.value = data.matrix
  } catch (err: any) {
    ElMessage.error('获取房态数据失败')
  } finally {
    loading.value = false
  }
}

function formatDate(d: Date | string) {
  if (typeof d === 'string') return d
  return d.toISOString().slice(0, 10)
}

/// Cell helpers
function cellStatus(roomId: number, d: string): string {
  return matrix.value[String(roomId)]?.[d] ?? 'available'
}

const cellClassMap: Record<string, string> = {
  available: 'cell-available',
  held: 'cell-held',
  booked: 'cell-booked',
  maintenance: 'cell-maintenance',
}

const statusLabel: Record<string, string> = {
  available: '空闲',
  held: '锁房',
  booked: '已预订',
  maintenance: '维护',
}

const today = formatDate(new Date())

// Summary stats
const summary = computed(() => {
  const total = rooms.value.length * dates.value.length
  let available = 0, held = 0, booked = 0, maint = 0
  for (const rid of rooms.value) {
    for (const d of dates.value) {
      const s = cellStatus(rid.id, d)
      if (s === 'available') available++
      else if (s === 'held') held++
      else if (s === 'booked') booked++
      else if (s === 'maintenance') maint++
    }
  }
  return { available, held, booked, maintenance: maint, total }
})
</script>

<template>
  <div v-loading="loading" class="inventory-calendar-page">
    <div class="page-header">
      <div>
        <h3>房态日历看板</h3>
        <p>按房间 × 日期查看占用情况（绿色=空闲 / 黄色=锁房 / 红色=已预订 / 灰色=维护）</p>
      </div>
      <div class="header-actions">
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          value-format="YYYY-MM-DD"
          style="width: 260px"
          @change="loadMatrix"
        />
        <el-button type="primary" @click="loadMatrix">刷新</el-button>
      </div>
    </div>

    <!-- Summary chips -->
    <div class="summary-bar">
      <el-tag type="success">空闲 {{ summary.available }} 间次</el-tag>
      <el-tag type="warning">锁房 {{ summary.held }} 间次</el-tag>
      <el-tag type="danger">已预订 {{ summary.booked }} 间次</el-tag>
      <el-tag type="info">维护 {{ summary.maintenance }} 间次</el-tag>
      <span class="summary-total">覆盖 {{ dates.length }} 天 × {{ rooms.length }} 间房</span>
    </div>

    <!-- Matrix Table -->
    <div v-if="rooms.length && dates.length" class="matrix-wrapper">
      <el-table
        :data="rooms"
        border
        stripe
        size="small"
        :max-height="600"
        style="width: 100%"
      >
        <el-table-column type="index" label="#" width="48" fixed />
        <el-table-column prop="room_number" label="房号" width="80" fixed />
        <el-table-column prop="room_type" label="房型" width="120" fixed />
        <el-table-column
          v-for="d in dates"
          :key="d"
          :label="d"
          :width="80"
          align="center"
        >
          <template #default="{ row }">
            <div
              class="cell-box"
              :class="[cellClassMap[cellStatus(row.id, d)], { 'is-today': d === today }]"
              :title="`${row.room_number} · ${d} · ${statusLabel[cellStatus(row.id, d)]}`"
            >
              <span class="cell-dot" />
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- Empty -->
    <el-empty v-else description="暂无房间数据，请先创建客房" />
  </div>
</template>

<style scoped>
.inventory-calendar-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 12px;
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

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.summary-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.summary-total {
  font-size: 12px;
  color: var(--text-muted);
  margin-left: 8px;
}

.matrix-wrapper {
  overflow-x: auto;
  border: 1px solid var(--card-border);
  border-radius: var(--radius-md);
  background: #fff;
}

.cell-box {
  width: 100%;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 3px;
}

.cell-dot {
  width: 14px;
  height: 14px;
  border-radius: 3px;
}

.cell-available .cell-dot {
  background: #10b981;
}

.cell-held .cell-dot {
  background: #f59e0b;
}

.cell-booked .cell-dot {
  background: #ef4444;
}

.cell-maintenance .cell-dot {
  background: #94a3b8;
}

.cell-box.is-today {
  outline: 2px solid #6366f1;
  outline-offset: 1px;
}
</style>

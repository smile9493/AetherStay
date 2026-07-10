<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api'
import { Calendar } from '@element-plus/icons-vue'
import AdminPagination from '@/components/admin/AdminPagination.vue'
import { usePagination } from '@/composables/usePagination'

const loading = ref(false)
const { currentPage, pageSize, total, pageStart, pageEnd, resetPage } = usePagination(10)

interface InventoryResponse {
  rooms: { id: number; room_number: string; room_type: string }[]
  dates: string[]
  matrix: Record<string, Record<string, string>>
  total: number
  page: number
  page_size: number
}

const dateRange = ref<[Date, Date] | [string, string]>([
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
    const { data } = await api.get<InventoryResponse>('/admin/inventory', {
      params: {
        start_date: start,
        end_date: end,
        page: currentPage.value,
        page_size: pageSize.value,
      },
    })
    rooms.value = data.rooms
    dates.value = data.dates
    matrix.value = data.matrix
    total.value = data.total
    currentPage.value = data.page
    pageSize.value = data.page_size
  } catch {
    ElMessage.error('获取房态数据失败')
  } finally {
    loading.value = false
  }
}

function onDateRangeChange() {
  resetPage()
  loadMatrix()
}

function handlePageChange(page: number) {
  currentPage.value = page
  loadMatrix()
}

function handleSizeChange(size: number) {
  pageSize.value = size
  currentPage.value = 1
  loadMatrix()
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
    <!-- Header banner -->
    <div class="page-header">
      <div class="page-header-left">
        <div class="header-icon">
          <el-icon><Calendar /></el-icon>
        </div>
        <div class="title-cell">
          <h3>房态日历看板</h3>
          <p>实时监控物理房间在选定日期范围内的预约与锁房情况（绿色=空闲 / 黄色=锁房 / 红色=已预订 / 灰色=维护）。</p>
        </div>
      </div>
      <div class="header-actions">
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          value-format="YYYY-MM-DD"
          class="custom-date-range"
          @change="onDateRangeChange"
        />
        <el-button type="primary" class="refresh-btn" @click="loadMatrix">刷新</el-button>
      </div>
    </div>

    <!-- Summary Statistics Bar -->
    <div class="summary-bar-premium glass-panel-inner">
      <div class="stats-pills-row">
        <span class="pill-badge available">空闲 {{ summary.available }} 间次</span>
        <span class="pill-badge held">锁房 {{ summary.held }} 间次</span>
        <span class="pill-badge booked">已订 {{ summary.booked }} 间次</span>
        <span class="pill-badge maintenance">维护 {{ summary.maintenance }} 间次</span>
      </div>
      <span class="summary-total">
        本页 {{ rooms.length }} 间房 × {{ dates.length }} 天（共 {{ total }} 间房）
      </span>
    </div>

    <!-- Matrix Table Grid -->
    <div v-if="rooms.length && dates.length" class="matrix-wrapper shadow-premium">
      <el-table
        :data="rooms"
        border
        size="small"
        :max-height="600"
        class="calendar-matrix-table"
        style="width: 100%"
      >
        <el-table-column type="index" label="#" width="50" align="center" fixed />
        
        <!-- Room Number -->
        <el-table-column prop="room_number" label="客房号" width="90" align="center" fixed>
          <template #default="{ row }">
            <span class="room-number-text">Room {{ row.room_number }}</span>
          </template>
        </el-table-column>
        
        <!-- Room Type -->
        <el-table-column prop="room_type" label="客房房型" width="130" fixed>
          <template #default="{ row }">
            <span class="room-type-text">{{ row.room_type }}</span>
          </template>
        </el-table-column>
        
        <!-- Dates columns dynamically rendered -->
        <el-table-column
          v-for="d in dates"
          :key="d"
          :label="d"
          :width="90"
          align="center"
        >
          <template #header>
            <div class="date-header-cell" :class="{ 'is-today': d === today }">
              <span class="month-day">{{ d.slice(5) }}</span>
              <span v-if="d === today" class="today-tag">今天</span>
            </div>
          </template>
          
          <template #default="{ row }">
            <div
              class="cell-box"
              :class="[cellClassMap[cellStatus(row.id, d)], { 'is-today': d === today }]"
              :title="`${row.room_number} · ${d} · ${statusLabel[cellStatus(row.id, d)]}`"
            >
              <div class="status-core">
                <span class="status-indicator-dot" />
                <span class="status-label-mini">{{ statusLabel[cellStatus(row.id, d)] }}</span>
              </div>
            </div>
          </template>
        </el-table-column>
      </el-table>
      <AdminPagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="total"
        :page-start="pageStart"
        :page-end="pageEnd"
        @page-change="handlePageChange"
        @size-change="handleSizeChange"
      />
    </div>

    <!-- Empty view -->
    <div v-else class="empty-calendar-wrapper glass-panel">
      <el-empty :image-size="80" description="暂无客房数据，请前往客房资源录入客房" />
    </div>
  </div>
</template>

<style scoped>
.inventory-calendar-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}

.page-header-left {
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

.title-cell h3 {
  font-size: 20px;
  font-weight: 800;
  color: var(--text-primary);
}

.title-cell p {
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: 2px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.custom-date-range {
  width: 280px !important;
  background: rgba(255, 255, 255, 0.6) !important;
  border-radius: var(--radius-sm);
}

.refresh-btn {
  background: var(--accent-gradient);
  border: none;
  font-weight: 600;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.2);
}

/* Premium Statistics Bar */
.summary-bar-premium {
  background: rgba(255, 255, 255, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.4);
  padding: 14px 20px;
  border-radius: var(--radius-lg);
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
  box-shadow: 0 10px 25px -10px rgba(99, 102, 241, 0.04);
}

.stats-pills-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.pill-badge {
  font-size: 11px;
  font-weight: 700;
  padding: 4px 12px;
  border-radius: 20px;
}

.pill-badge.available { background: #ecfdf5; color: #059669; border: 1px solid #d1fae5; }
.pill-badge.held { background: #fffbeb; color: #d97706; border: 1px solid #fef3c7; }
.pill-badge.booked { background: #fdf2f2; color: #dc2626; border: 1px solid #fde8e8; }
.pill-badge.maintenance { background: #f8fafc; color: #475569; border: 1px solid #e2e8f0; }

.summary-total {
  font-size: 12px;
  color: var(--text-muted);
  font-weight: 600;
}

/* Matrix Table styling */
.matrix-wrapper {
  background: rgba(255, 255, 255, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.4);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.shadow-premium {
  box-shadow: 0 15px 35px -10px rgba(99, 102, 241, 0.08);
}

.calendar-matrix-table {
  background: transparent !important;
}

.calendar-matrix-table :deep(tr) {
  background: transparent !important;
}

.calendar-matrix-table :deep(th.el-table__cell) {
  background: rgba(255, 255, 255, 0.8) !important;
  font-weight: 700;
  color: var(--text-primary);
  font-size: 13px;
  padding: 12px 0;
  border-bottom: 1px solid rgba(99, 102, 241, 0.1);
}

.calendar-matrix-table :deep(td.el-table__cell) {
  padding: 10px 0;
  border-bottom: 1px solid rgba(99, 102, 241, 0.05);
}

.room-number-text {
  font-family: var(--font-title);
  font-weight: 700;
  color: var(--text-primary);
  font-size: 13px;
}

.room-type-text {
  font-size: 12px;
  color: var(--text-secondary);
  font-weight: 600;
}

/* Dynamic header dates */
.date-header-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.date-header-cell.is-today {
  color: var(--primary-color);
}

.date-header-cell .month-day {
  font-family: var(--font-title);
  font-weight: 700;
}

.date-header-cell .today-tag {
  font-size: 9px;
  font-weight: 800;
  background: var(--accent-gradient);
  color: #fff;
  padding: 1px 4px;
  border-radius: 4px;
  margin-top: 2px;
  line-height: 1;
}

/* Custom Grid Cell Box Styles */
.cell-box {
  width: 100%;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  transition: all 0.2s;
  cursor: pointer;
  border: 1px solid transparent;
}

.cell-box:hover {
  transform: scale(1.05);
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.06);
}

.status-core {
  display: flex;
  align-items: center;
  gap: 6px;
}

.status-indicator-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-label-mini {
  font-size: 11px;
  font-weight: 700;
}

/* Color codes */
.cell-available {
  background: #ecfdf5;
  border-color: rgba(16, 185, 129, 0.15);
}
.cell-available .status-indicator-dot { background: #10b981; }
.cell-available .status-label-mini { color: #059669; }

.cell-held {
  background: #fffbeb;
  border-color: rgba(245, 158, 11, 0.15);
}
.cell-held .status-indicator-dot { background: #f59e0b; }
.cell-held .status-label-mini { color: #d97706; }

.cell-booked {
  background: #fdf2f2;
  border-color: rgba(239, 68, 68, 0.15);
}
.cell-booked .status-indicator-dot { background: #ef4444; }
.cell-booked .status-label-mini { color: #dc2626; }

.cell-maintenance {
  background: #f8fafc;
  border-color: rgba(148, 163, 184, 0.15);
}
.cell-maintenance .status-indicator-dot { background: #94a3b8; }
.cell-maintenance .status-label-mini { color: #475569; }

.cell-box.is-today {
  outline: 2px solid var(--primary-color);
  outline-offset: 1px;
}

.empty-calendar-wrapper {
  padding: 56px;
  text-align: center;
}
</style>

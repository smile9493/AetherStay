<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api'
import { Ticket, House, User, TrendCharts, Money, Calendar, ArrowRight } from '@element-plus/icons-vue'

const loading = ref(false)
const stats = ref({
  total_bookings: 0,
  pending_bookings: 0,
  confirmed_bookings: 0,
  active_check_ins: 0,
  total_revenue: 0,
  total_rooms: 0,
  active_rooms: 0,
  total_users: 0,
  active_users: 0,
})

const recentBookings = ref<any[]>([])

onMounted(loadDashboardData)

async function loadDashboardData() {
  loading.value = true
  try {
    const [statsRes, bookingsRes] = await Promise.all([
      api.get('/admin/stats'),
      api.get<{ items: any[] }>('/admin/bookings', { params: { page: 1, page_size: 5 } }),
    ])

    stats.value = statsRes.data
    recentBookings.value = bookingsRes.data.items
    
  } catch (err: any) {
    ElMessage.error('获取大盘数据失败，请检查您的管理权限')
  } finally {
    loading.value = false
  }
}

const occupancyRate = computed(() => {
  if (stats.value.total_rooms === 0) return 0
  return Math.round((stats.value.active_check_ins / stats.value.total_rooms) * 100)
})

const bookingStatusMap: Record<string, { text: string; type: 'warning' | 'success' | 'primary' | 'info' | 'danger'; gradient: string }> = {
  pending: { text: '待付款', type: 'warning', gradient: 'linear-gradient(135deg, #ff9800 0%, #ff5722 100%)' },
  confirmed: { text: '已确认', type: 'success', gradient: 'linear-gradient(135deg, #4caf50 0%, #2e7d32 100%)' },
  checked_in: { text: '已入住', type: 'primary', gradient: 'linear-gradient(135deg, #2196f3 0%, #1565c0 100%)' },
  checked_out: { text: '已退房', type: 'info', gradient: 'linear-gradient(135deg, #9e9e9e 0%, #424242 100%)' },
  cancelled: { text: '已取消', type: 'danger', gradient: 'linear-gradient(135deg, #f44336 0%, #c62828 100%)' },
}
</script>

<template>
  <div v-loading="loading" class="admin-dashboard-page">
    <!-- Header banner -->
    <div class="dashboard-header-row">
      <div class="title-cell">
        <h3>控制台数据大盘</h3>
        <p>AetherStay 核心指标监控与全局客房状态分析</p>
      </div>
      <el-button type="primary" class="refresh-btn" :icon="TrendCharts" @click="loadDashboardData">
        刷新实时状态
      </el-button>
    </div>

    <!-- KPI Summary Grid -->
    <el-row :gutter="20" class="kpi-row">
      <!-- Card 1: Revenue -->
      <el-col :xs="24" :sm="12" :md="6">
        <div class="kpi-glass-card card-revenue">
          <div class="card-glow" />
          <div class="card-content">
            <span class="kpi-label">营业总收入</span>
            <h2 class="kpi-value">¥{{ stats.total_revenue.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}</h2>
            <span class="kpi-subtext">在线实付流水总计</span>
          </div>
          <div class="icon-bubble bg-green">
            <el-icon><Money /></el-icon>
          </div>
        </div>
      </el-col>
      <!-- Card 2: Bookings -->
      <el-col :xs="24" :sm="12" :md="6">
        <div class="kpi-glass-card card-bookings">
          <div class="card-glow" />
          <div class="card-content">
            <span class="kpi-label">总订单数量</span>
            <h2 class="kpi-value">{{ stats.total_bookings }} <span class="unit">笔</span></h2>
            <span class="kpi-subtext">全通道生成订单总和</span>
          </div>
          <div class="icon-bubble bg-indigo">
            <el-icon><Ticket /></el-icon>
          </div>
        </div>
      </el-col>
      <!-- Card 3: Check-ins -->
      <el-col :xs="24" :sm="12" :md="6">
        <div class="kpi-glass-card card-checkins">
          <div class="card-glow" />
          <div class="card-content">
            <span class="kpi-label">当前入住中</span>
            <h2 class="kpi-value">{{ stats.active_check_ins }} <span class="unit">间</span></h2>
            <span class="kpi-subtext">实时在住客房统计</span>
          </div>
          <div class="icon-bubble bg-blue">
            <el-icon><House /></el-icon>
          </div>
        </div>
      </el-col>
      <!-- Card 4: Users -->
      <el-col :xs="24" :sm="12" :md="6">
        <div class="kpi-glass-card card-users">
          <div class="card-glow" />
          <div class="card-content">
            <span class="kpi-label">活跃用户数</span>
            <h2 class="kpi-value">{{ stats.total_users }} <span class="unit">名</span></h2>
            <span class="kpi-subtext">注册贵宾及系统用户</span>
          </div>
          <div class="icon-bubble bg-purple">
            <el-icon><User /></el-icon>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- Visual charts row -->
    <el-row :gutter="24" class="charts-row">
      <!-- Occupancy Chart Widget -->
      <el-col :xs="24" :lg="11">
        <div class="dashboard-widget-card glass-panel-inner">
          <div class="widget-header">
            <h4>房间实时占用率</h4>
            <span class="sub">Occupancy Rate</span>
          </div>
          <div class="occupancy-widget-body">
            <div class="progress-container">
              <el-progress 
                type="dashboard" 
                :percentage="occupancyRate" 
                :stroke-width="14"
                :width="160"
                :color="[
                  { color: '#10b981', percentage: 40 },
                  { color: '#6366f1', percentage: 80 },
                  { color: '#f43f5e', percentage: 100 }
                ]"
              />
              <div class="progress-custom-label">
                <span class="pct">{{ occupancyRate }}%</span>
                <span class="lbl">占用率</span>
              </div>
            </div>
            
            <div class="occupancy-stats">
              <div class="stat-pills">
                <div class="stat-pill-item">
                  <span class="dot active"></span>
                  <span class="lbl">总客房数</span>
                  <span class="val">{{ stats.total_rooms }} 间</span>
                </div>
                <div class="stat-pill-item">
                  <span class="dot booked"></span>
                  <span class="lbl">在住占用</span>
                  <span class="val">{{ stats.active_check_ins }} 间</span>
                </div>
                <div class="stat-pill-item">
                  <span class="dot hold"></span>
                  <span class="lbl">待付款锁房</span>
                  <span class="val">{{ stats.pending_bookings }} 间</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </el-col>

      <!-- Recent Orders List Widget -->
      <el-col :xs="24" :lg="13">
        <div class="dashboard-widget-card glass-panel-inner">
          <div class="widget-header space-between">
            <div>
              <h4>最新调度预订</h4>
              <span class="sub">Recent Booking Actions</span>
            </div>
            <router-link to="/admin/bookings" class="view-all-link">
              <span>全部调度</span>
              <el-icon><ArrowRight /></el-icon>
            </router-link>
          </div>
          
          <div class="recent-bookings-flow">
            <transition-group name="list" tag="div" class="flow-container">
              <div 
                v-for="item in recentBookings" 
                :key="item.id" 
                class="flow-card-item"
              >
                <div class="user-avatar-badge">
                  <span class="initial">{{ item.room?.room_number ?? item.room_id }}</span>
                </div>
                <div class="flow-mid">
                  <div class="mid-header">
                    <span class="booking-id">#{{ item.id }}</span>
                    <span class="room-type-lbl">{{ item.room?.room_type?.name ?? '标准双床房' }}</span>
                  </div>
                  <div class="mid-dates">
                    <el-icon><Calendar /></el-icon>
                    <span>{{ item.check_in }} 至 {{ item.check_out }}</span>
                  </div>
                </div>
                <div class="flow-right">
                  <span class="price-lbl">¥{{ item.total_price }}</span>
                  <span 
                    class="status-glass-badge" 
                    :class="item.status"
                  >
                    {{ bookingStatusMap[item.status]?.text || item.status }}
                  </span>
                </div>
              </div>
            </transition-group>
            
            <div v-if="recentBookings.length === 0" class="empty-flow">
              <el-empty :image-size="60" description="暂无近期调度订单" />
            </div>
          </div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.admin-dashboard-page {
  display: flex;
  flex-direction: column;
  gap: 28px;
}

.dashboard-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}

.title-cell h3 {
  font-size: 22px;
  font-weight: 800;
  color: var(--text-primary);
  letter-spacing: -0.02em;
}

.title-cell p {
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: 4px;
}

.refresh-btn {
  background: var(--accent-gradient);
  border: none;
  font-weight: 600;
  box-shadow: 0 4px 14px -3px rgba(99, 102, 241, 0.4);
  transition: all 0.3s;
}

.refresh-btn:hover {
  opacity: 0.95;
  transform: translateY(-1px);
}

/* KPI Glass Cards */
.kpi-row {
  margin-bottom: 8px;
}

.kpi-glass-card {
  position: relative;
  background: rgba(255, 255, 255, 0.55);
  border: 1px solid rgba(255, 255, 255, 0.5);
  border-radius: var(--radius-lg);
  padding: 24px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  overflow: hidden;
  box-shadow: 0 10px 25px -10px rgba(99, 102, 241, 0.05);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  margin-bottom: 16px;
}

.kpi-glass-card:hover {
  transform: translateY(-4px) scale(1.01);
  box-shadow: 0 20px 35px -15px rgba(99, 102, 241, 0.15);
  background: rgba(255, 255, 255, 0.8);
}

.card-glow {
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: radial-gradient(circle, rgba(99, 102, 241, 0.04) 0%, transparent 60%);
  pointer-events: none;
  transition: all 0.5s;
}

.kpi-glass-card:hover .card-glow {
  transform: translate(10%, 10%);
}

.card-content {
  display: flex;
  flex-direction: column;
  z-index: 1;
}

.kpi-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.kpi-value {
  font-size: 24px;
  font-weight: 800;
  color: var(--text-primary);
  margin: 6px 0;
  font-family: var(--font-title);
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.kpi-value .unit {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
}

.kpi-subtext {
  font-size: 11px;
  color: var(--text-secondary);
  opacity: 0.8;
}

.icon-bubble {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  z-index: 1;
  box-shadow: 0 8px 16px -4px rgba(0, 0, 0, 0.05);
}

.icon-bubble.bg-green { background: #ecfdf5; color: #10b981; border: 1px solid #d1fae5; }
.icon-bubble.bg-indigo { background: #eef2ff; color: #6366f1; border: 1px solid #e0e7ff; }
.icon-bubble.bg-blue { background: #eff6ff; color: #3b82f6; border: 1px solid #dbeafe; }
.icon-bubble.bg-purple { background: #f5f3ff; color: #8b5cf6; border: 1px solid #ede9fe; }

/* Dashboard Widgets */
.dashboard-widget-card {
  padding: 24px;
  background: rgba(255, 255, 255, 0.45);
  border: 1px solid rgba(255, 255, 255, 0.5);
  border-radius: var(--radius-lg);
  box-shadow: 0 10px 30px -10px rgba(99, 102, 241, 0.04);
  margin-bottom: 24px;
}

.widget-header {
  margin-bottom: 24px;
}

.widget-header.space-between {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.widget-header h4 {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
}

.widget-header .sub {
  font-size: 11px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  display: block;
  margin-top: 2px;
}

.view-all-link {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--primary-color);
  font-weight: 600;
  text-decoration: none;
  transition: transform 0.2s;
}

.view-all-link:hover {
  transform: translateX(3px);
}

/* Occupancy layout */
.occupancy-widget-body {
  display: flex;
  align-items: center;
  justify-content: space-around;
  padding: 12px 0;
  gap: 20px;
}

.progress-container {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.progress-custom-label {
  position: absolute;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.progress-custom-label .pct {
  font-family: var(--font-title);
  font-size: 26px;
  font-weight: 800;
  color: var(--text-primary);
}

.progress-custom-label .lbl {
  font-size: 10px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-top: -2px;
}

.occupancy-stats {
  flex: 1;
  max-width: 240px;
}

.stat-pills {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.stat-pill-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: rgba(255, 255, 255, 0.6);
  border: 1px solid rgba(99, 102, 241, 0.05);
  border-radius: var(--radius-md);
  font-size: 12px;
}

.stat-pill-item .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.stat-pill-item .dot.active { background: #10b981; }
.stat-pill-item .dot.booked { background: #3b82f6; }
.stat-pill-item .dot.hold { background: #f59e0b; }

.stat-pill-item .lbl {
  color: var(--text-secondary);
  flex: 1;
}

.stat-pill-item .val {
  font-weight: 700;
  color: var(--text-primary);
}

/* Recent Bookings Cards Feed */
.recent-bookings-flow {
  max-height: 310px;
  overflow-y: auto;
  padding-right: 4px;
}

.flow-card-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.55);
  border: 1px solid rgba(99, 102, 241, 0.05);
  border-radius: var(--radius-md);
  margin-bottom: 12px;
  transition: all 0.25s ease;
}

.flow-card-item:hover {
  transform: translateY(-2px);
  background: #ffffff;
  box-shadow: 0 8px 20px -8px rgba(99, 102, 241, 0.1);
  border-color: rgba(99, 102, 241, 0.15);
}

.user-avatar-badge {
  width: 42px;
  height: 42px;
  border-radius: 10px;
  background: var(--primary-light);
  border: 1px solid rgba(99, 102, 241, 0.1);
  color: var(--primary-color);
  font-family: var(--font-title);
  font-weight: 800;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.flow-mid {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.flow-mid .mid-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.flow-mid .booking-id {
  font-family: monospace;
  font-weight: 700;
  font-size: 13px;
  color: var(--text-primary);
}

.flow-mid .room-type-lbl {
  font-size: 12px;
  color: var(--text-secondary);
  font-weight: 500;
}

.flow-mid .mid-dates {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--text-muted);
}

.flow-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
}

.flow-right .price-lbl {
  font-size: 14px;
  font-weight: 800;
  color: var(--primary-color);
  font-family: var(--font-title);
}

.status-glass-badge {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 20px;
  text-transform: uppercase;
}

.status-glass-badge.pending { background: #fffbeb; color: #d97706; border: 1px solid #fef3c7; }
.status-glass-badge.confirmed { background: #ecfdf5; color: #059669; border: 1px solid #d1fae5; }
.status-glass-badge.checked_in { background: #eff6ff; color: #2563eb; border: 1px solid #dbeafe; }
.status-glass-badge.checked_out { background: #f8fafc; color: #475569; border: 1px solid #e2e8f0; }
.status-glass-badge.cancelled { background: #fdf2f2; color: #dc2626; border: 1px solid #fde8e8; }

.empty-flow {
  padding: 40px 0;
  text-align: center;
}

@media (max-width: 768px) {
  .occupancy-widget-body {
    flex-direction: column;
  }
}
</style>

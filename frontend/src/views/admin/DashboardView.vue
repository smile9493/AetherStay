<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api'
import { Ticket, House, User, TrendCharts, Money } from '@element-plus/icons-vue'

const loading = ref(false)
const stats = ref({
  totalBookings: 0,
  pendingBookings: 0,
  activeCheckIns: 0,
  totalRevenue: 0,
  totalRooms: 0,
  activeRooms: 0,
  totalUsers: 0,
  activeUsers: 0,
})

const recentBookings = ref<any[]>([])

onMounted(loadDashboardData)

async function loadDashboardData() {
  loading.value = true
  try {
    const [bookingsRes, roomsRes, usersRes] = await Promise.all([
      api.get<any[]>('/admin/bookings'),
      api.get<any[]>('/admin/rooms'),
      api.get<any[]>('/admin/users')
    ])
    
    const bookings = bookingsRes.data
    const rooms = roomsRes.data
    const users = usersRes.data
    
    // Calculate statistics
    stats.value.totalBookings = bookings.length
    stats.value.pendingBookings = bookings.filter(b => b.status === 'pending').length
    stats.value.activeCheckIns = bookings.filter(b => b.status === 'checked_in').length
    
    // Revenue from confirmed/checked_in/checked_out orders
    stats.value.totalRevenue = bookings
      .filter(b => ['confirmed', 'checked_in', 'checked_out'].includes(b.status))
      .reduce((acc, b) => acc + parseFloat(b.total_price), 0)
      
    stats.value.totalRooms = rooms.length
    stats.value.activeRooms = rooms.filter(r => r.status === 'active').length
    
    stats.value.totalUsers = users.length
    stats.value.activeUsers = users.filter(u => u.is_active).length
    
    // Get top 5 recent bookings
    recentBookings.value = bookings.slice(0, 5)
    
  } catch (err: any) {
    ElMessage.error('获取大盘数据失败，请检查您的管理权限')
  } finally {
    loading.value = false
  }
}

const occupancyRate = computed(() => {
  if (stats.value.totalRooms === 0) return 0
  return Math.round((stats.value.activeCheckIns / stats.value.totalRooms) * 100)
})

import { computed } from 'vue'
</script>

<template>
  <div v-loading="loading" class="admin-dashboard-page">
    <div class="dashboard-header-row">
      <div class="title-cell">
        <h3>系统运行状态监控</h3>
        <p>实时汇聚分析客房占用、营收指标以及高并发锁状态</p>
      </div>
      <el-button type="primary" :icon="TrendCharts" @click="loadDashboardData">
        刷新实时状态
      </el-button>
    </div>

    <!-- KPI Summary Grid -->
    <el-row :gutter="20" class="kpi-row">
      <el-col :xs="24" :sm="12" :md="6">
        <el-card class="kpi-card shadow-sm" body-style="padding: 20px;">
          <div class="kpi-card-inner">
            <div class="text-group">
              <span class="kpi-label">营业总收入</span>
              <span class="kpi-value">¥{{ stats.totalRevenue.toFixed(2) }}</span>
            </div>
            <div class="icon-wrapper bg-green">
              <el-icon><Money /></el-icon>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <el-card class="kpi-card shadow-sm" body-style="padding: 20px;">
          <div class="kpi-card-inner">
            <div class="text-group">
              <span class="kpi-label">总订单数量</span>
              <span class="kpi-value">{{ stats.totalBookings }} 笔</span>
            </div>
            <div class="icon-wrapper bg-indigo">
              <el-icon><Ticket /></el-icon>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <el-card class="kpi-card shadow-sm" body-style="padding: 20px;">
          <div class="kpi-card-inner">
            <div class="text-group">
              <span class="kpi-label">当前入住中</span>
              <span class="kpi-value">{{ stats.activeCheckIns }} 间</span>
            </div>
            <div class="icon-wrapper bg-blue">
              <el-icon><House /></el-icon>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <el-card class="kpi-card shadow-sm" body-style="padding: 20px;">
          <div class="kpi-card-inner">
            <div class="text-group">
              <span class="kpi-label">注册用户数</span>
              <span class="kpi-value">{{ stats.totalUsers }} 名</span>
            </div>
            <div class="icon-wrapper bg-purple">
              <el-icon><User /></el-icon>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Visual charts row -->
    <el-row :gutter="20" class="charts-row mt-4">
      <el-col :xs="24" :md="12">
        <el-card class="dashboard-widget shadow-sm">
          <template #header>
            <div class="widget-header">
              <span>房间资源占用分析 (Occupancy Rate)</span>
            </div>
          </template>
          <div class="occupancy-widget-body">
            <el-progress 
              type="dashboard" 
              :percentage="occupancyRate" 
              :color="['#6366f1', '#8b5cf6', '#ef4444']"
              :stroke-width="12"
            />
            <div class="occupancy-stats">
              <div class="stat-bullet">
                <span class="dot active"></span>
                <span>客房总数：{{ stats.totalRooms }} 间</span>
              </div>
              <div class="stat-bullet">
                <span class="dot booked"></span>
                <span>当前入住：{{ stats.activeCheckIns }} 间</span>
              </div>
              <div class="stat-bullet">
                <span class="dot hold"></span>
                <span>待付款锁房：{{ stats.pendingBookings }} 间</span>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- Recent logs -->
      <el-col :xs="24" :md="12">
        <el-card class="dashboard-widget shadow-sm">
          <template #header>
            <div class="widget-header">
              <span>最新提交订单</span>
            </div>
          </template>
          <div class="recent-bookings-list">
            <div 
              v-for="item in recentBookings" 
              :key="item.id" 
              class="recent-booking-item"
            >
              <div class="item-left">
                <span class="lbl-id">#{{ item.id }}</span>
                <span class="lbl-room">Room {{ item.room?.room_number }}</span>
              </div>
              <div class="item-center">
                <span class="lbl-dates">{{ item.check_in }} 至 {{ item.check_out }}</span>
              </div>
              <div class="item-right">
                <span class="lbl-price">¥{{ item.total_price }}</span>
                <el-tag 
                  size="small" 
                  :type="item.status === 'confirmed' ? 'success' : item.status === 'pending' ? 'warning' : 'info'"
                >
                  {{ item.status }}
                </el-tag>
              </div>
            </div>
            <div v-if="recentBookings.length === 0" class="empty-recent">
              暂无新订单信息
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.admin-dashboard-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.dashboard-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.title-cell h3 {
  font-size: 20px;
  font-weight: 700;
  margin-bottom: 4px;
}

.title-cell p {
  font-size: 13px;
  color: var(--text-secondary);
}

/* KPI Summary */
.kpi-row {
  margin-bottom: 12px;
}

.kpi-card {
  border-radius: var(--radius-md);
  border: 1px solid var(--card-border);
}

.kpi-card-inner {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.text-group {
  display: flex;
  flex-direction: column;
}

.kpi-label {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 6px;
  font-weight: 500;
}

.kpi-value {
  font-size: 22px;
  font-weight: 800;
  color: var(--text-primary);
  font-family: var(--font-title);
}

.icon-wrapper {
  padding: 12px;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
}

.icon-wrapper.bg-green { background: #f0fdf4; color: #10b981; }
.icon-wrapper.bg-indigo { background: #eef2ff; color: #6366f1; }
.icon-wrapper.bg-blue { background: #eff6ff; color: #3b82f6; }
.icon-wrapper.bg-purple { background: #f5f3ff; color: #8b5cf6; }

/* Dashboard Widgets */
.dashboard-widget {
  border-radius: var(--radius-md);
  border: 1px solid var(--card-border);
  min-height: 280px;
}

.widget-header {
  font-size: 14px;
  font-weight: 600;
}

.occupancy-widget-body {
  display: flex;
  align-items: center;
  justify-content: space-around;
  padding: 12px 0;
}

@media (max-width: 576px) {
  .occupancy-widget-body {
    flex-direction: column;
    gap: 20px;
  }
}

.occupancy-stats {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.stat-bullet {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: var(--text-secondary);
}

.stat-bullet .dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.stat-bullet .dot.active { background: #3b82f6; }
.stat-bullet .dot.booked { background: #10b981; }
.stat-bullet .dot.hold { background: #f59e0b; }

/* Recent Bookings */
.recent-bookings-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.recent-booking-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  background: #f8fafc;
  border-radius: var(--radius-sm);
  border: 1px solid var(--card-border);
}

.item-left {
  display: flex;
  flex-direction: column;
}

.item-left .lbl-id {
  font-family: monospace;
  font-weight: 700;
  font-size: 13px;
  color: var(--text-primary);
}

.item-left .lbl-room {
  font-size: 11px;
  color: var(--text-muted);
}

.item-center .lbl-dates {
  font-size: 12px;
  color: var(--text-secondary);
}

.item-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.item-right .lbl-price {
  font-weight: 700;
  font-size: 13px;
  color: var(--primary-color);
}

.empty-recent {
  padding: 40px;
  text-align: center;
  color: var(--text-muted);
  font-size: 13px;
}

.mt-4 {
  margin-top: 16px;
}
</style>

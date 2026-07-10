import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: () => import('@/layouts/MainLayout.vue'),
      children: [
        { path: '', name: 'home', component: () => import('@/views/HomeView.vue') },
        { path: 'rooms', name: 'rooms', component: () => import('@/views/RoomsView.vue') },
        { path: 'bookings', name: 'bookings', component: () => import('@/views/BookingsView.vue'), meta: { requiresAuth: true } },
        {
          path: 'admin',
          component: () => import('@/layouts/AdminLayout.vue'),
          meta: { requiresAuth: true, requiresAdmin: true },
          children: [
            { path: '', redirect: '/admin/dashboard' },
            { path: 'dashboard', name: 'admin-dashboard', component: () => import('@/views/admin/DashboardView.vue') },
            { path: 'bookings', name: 'admin-bookings', component: () => import('@/views/admin/AdminBookingsView.vue') },
            { path: 'rooms', name: 'admin-rooms', component: () => import('@/views/admin/AdminRoomsView.vue') },
            { path: 'room-types', name: 'admin-room-types', component: () => import('@/views/admin/AdminRoomTypesView.vue') },
            { path: 'inventory', name: 'admin-inventory', component: () => import('@/views/admin/InventoryCalendarView.vue') },
            { path: 'users', name: 'admin-users', component: () => import('@/views/admin/AdminUsersView.vue') },
            { path: 'settings', name: 'admin-settings', component: () => import('@/views/admin/AdminSettingsView.vue') },
          ]
        }
      ],
    },
    { path: '/login', name: 'login', component: () => import('@/views/LoginView.vue') },
    { path: '/register', name: 'register', component: () => import('@/views/RegisterView.vue') },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  
  // Ensure we fetch current user if not already set in Pinia
  if (!auth.user) {
    await auth.fetchUser()
  }
  
  // 1. Check login requirements
  if (to.meta.requiresAuth && !auth.user) {
    ElMessage.warning('请先登录以访问此页面')
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  
  // 2. Check admin RBAC requirements
  if (to.meta.requiresAdmin) {
    if (!auth.user || auth.user.role !== 'admin') {
      ElMessage.error('越权警告：该区域仅限系统管理员访问')
      return { name: 'home' }
    }
  }
})

export default router

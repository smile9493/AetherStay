import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

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
      ],
    },
    { path: '/login', name: 'login', component: () => import('@/views/LoginView.vue') },
    { path: '/register', name: 'register', component: () => import('@/views/RegisterView.vue') },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.user) {
    await auth.fetchUser()
    if (!auth.user) return { name: 'login', query: { redirect: to.fullPath } }
  }
})

export default router

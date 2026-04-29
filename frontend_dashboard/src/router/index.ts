import { createRouter, createWebHistory } from 'vue-router';
import { useAuthStore } from '@/store';

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginView.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('@/views/DashboardView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/history',
    name: 'History',
    component: () => import('@/views/HistoryView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/devices',
    name: 'Devices',
    component: () => import('@/views/DevicesView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/tasks',
    name: 'Tasks',
    component: () => import('@/views/TasksView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/users',
    name: 'Users',
    component: () => import('@/views/UsersView.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFound.vue'),
    meta: { requiresAuth: false }
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

// Route guards
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore();

  // Initialize auth on first navigation
  if (!authStore.user && !authStore.token) {
    authStore.initializeAuth();
  }

  const requiresAuth = to.meta.requiresAuth !== false;
  const requiresAdmin = to.meta.requiresAdmin === true;

  if (requiresAuth && !authStore.isAuthenticated) {
    // Redirect to login if authentication is required but user is not authenticated
    next('/login');
  } else if (requiresAdmin && !authStore.isAdmin) {
    // Redirect to dashboard if admin access is required but user is not admin
    next('/');
  } else {
    next();
  }
});

export default router;
<template>
  <div class="sidebar">
    <div class="sidebar-header">
      <h2 class="sidebar-title">矿山安全监控</h2>
    </div>

    <nav class="sidebar-nav">
      <router-link
        v-for="item in menuItems"
        :key="item.path"
        :to="item.path"
        class="nav-item"
        active-class="active"
      >
        <el-icon class="nav-icon">
          <component :is="item.icon" />
        </el-icon>
        <span class="nav-text">{{ item.label }}</span>
      </router-link>
    </nav>

    <div class="sidebar-footer">
      <div class="user-info">
        <div class="user-avatar">
          <el-icon><User /></el-icon>
        </div>
        <div class="user-details">
          <div class="user-name">{{ user?.full_name || user?.username }}</div>
          <div class="user-role">{{ getRoleLabel(user?.role) }}</div>
        </div>
      </div>
      <el-button
        link
        class="logout-btn"
        @click="handleLogout"
      >
        <el-icon><SwitchButton /></el-icon>
        退出登录
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRouter } from 'vue-router';
import {
  Monitor,
  DocumentCopy,
  Cpu,
  Tickets,
  User,
  SwitchButton
} from '@element-plus/icons-vue';
import { useAuthStore } from '@/store';

const router = useRouter();
const authStore = useAuthStore();

const user = computed(() => authStore.user);

const menuItems = computed(() => [
  {
    path: '/',
    label: '监控面板',
    icon: Monitor
  },
  {
    path: '/history',
    label: '历史记录',
    icon: DocumentCopy
  },
  {
    path: '/devices',
    label: '设备管理',
    icon: Cpu
  },
  {
    path: '/tasks',
    label: '任务管理',
    icon: Tickets
  },
  ...(authStore.isAdmin ? [{
    path: '/users',
    label: '用户管理',
    icon: User
  }] : [])
]);

const getRoleLabel = (role?: string) => {
  const roleMap = {
    admin: '管理员',
    operator: '操作员',
    viewer: '查看者'
  };
  return role ? roleMap[role as keyof typeof roleMap] : '未知';
};

const handleLogout = () => {
  authStore.logout();
  router.push('/login');
};
</script>

<style scoped>
.sidebar {
  @apply bg-gray-800 text-white h-full flex flex-col;
  width: 250px;
}

.sidebar-header {
  @apply p-6 border-b border-gray-700;
}

.sidebar-title {
  @apply text-xl font-bold text-center;
}

.sidebar-nav {
  @apply flex-1 py-4;
}

.nav-item {
  @apply flex items-center px-6 py-3 text-gray-300 hover:bg-gray-700 hover:text-white transition-colors;
  text-decoration: none;
}

.nav-item.active {
  @apply bg-blue-600 text-white;
}

.nav-icon {
  @apply mr-3;
}

.nav-text {
  @apply font-medium;
}

.sidebar-footer {
  @apply p-4 border-t border-gray-700;
}

.user-info {
  @apply flex items-center mb-4;
}

.user-avatar {
  @apply w-10 h-10 bg-gray-600 rounded-full flex items-center justify-center mr-3;
}

.user-details {
  @apply flex-1;
}

.user-name {
  @apply font-medium text-sm;
}

.user-role {
  @apply text-xs text-gray-400;
}

.logout-btn {
  @apply w-full text-left text-gray-300 hover:text-white;
}
</style>
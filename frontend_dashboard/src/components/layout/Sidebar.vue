<template>
  <div class="sidebar">
    <div class="sidebar-header">
      <div class="brand-mark">
        <el-icon><Monitor /></el-icon>
      </div>
      <h2 class="sidebar-title">矿山安全监控</h2>
      <span class="sidebar-subtitle">Hot Work Command</span>
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
  width: 250px;
  position: relative;
  z-index: 2;
  display: flex;
  height: 100%;
  flex-direction: column;
  color: var(--text-primary);
  background:
    linear-gradient(180deg, rgba(5, 23, 38, 0.94), rgba(3, 12, 23, 0.88)),
    rgba(3, 12, 23, 0.9);
  border-right: 1px solid rgba(126, 211, 255, 0.18);
  box-shadow: 12px 0 38px rgba(0, 0, 0, 0.22);
  backdrop-filter: blur(20px) saturate(130%);
}

.sidebar-header {
  display: grid;
  grid-template-columns: 42px 1fr;
  gap: 6px 12px;
  align-items: center;
  padding: 18px;
  border-bottom: 1px solid rgba(126, 211, 255, 0.14);
}

.brand-mark {
  display: flex;
  width: 42px;
  height: 42px;
  grid-row: span 2;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(28, 199, 255, 0.5);
  border-radius: 8px;
  color: #9aefff;
  background: rgba(28, 199, 255, 0.1);
  box-shadow: 0 0 22px rgba(28, 199, 255, 0.2);
}

.sidebar-title {
  margin: 0;
  color: #ffffff;
  font-size: 17px;
  font-weight: 800;
  line-height: 1.15;
  letter-spacing: 0;
}

.sidebar-subtitle {
  color: var(--text-muted);
  font-size: 11px;
  font-weight: 650;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.sidebar-nav {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 6px;
  padding: 14px 12px;
}

.nav-item {
  position: relative;
  display: flex;
  align-items: center;
  min-height: 42px;
  padding: 0 12px;
  border: 1px solid transparent;
  border-radius: 8px;
  color: var(--text-secondary);
  text-decoration: none;
  transition: border-color 0.2s ease, background 0.2s ease, color 0.2s ease, box-shadow 0.2s ease;
}

.nav-item:hover {
  color: #ffffff;
  border-color: rgba(126, 211, 255, 0.2);
  background: rgba(28, 199, 255, 0.08);
}

.nav-item.active {
  color: #ffffff;
  border-color: rgba(28, 199, 255, 0.52);
  background: linear-gradient(90deg, rgba(28, 199, 255, 0.22), rgba(28, 199, 255, 0.06));
  box-shadow: inset 3px 0 0 var(--accent-cyan), 0 0 20px rgba(28, 199, 255, 0.12);
}

.nav-icon {
  margin-right: 11px;
  color: #84e8ff;
  font-size: 18px;
}

.nav-text {
  font-size: 14px;
  font-weight: 700;
}

.sidebar-footer {
  padding: 14px;
  border-top: 1px solid rgba(126, 211, 255, 0.14);
}

.user-info {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
  padding: 10px;
  border: 1px solid rgba(126, 211, 255, 0.14);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.035);
}

.user-avatar {
  display: flex;
  width: 34px;
  height: 34px;
  align-items: center;
  justify-content: center;
  margin-right: 10px;
  border: 1px solid rgba(57, 231, 159, 0.32);
  border-radius: 50%;
  color: #8cf2c3;
  background: rgba(57, 231, 159, 0.1);
}

.user-details {
  min-width: 0;
  flex: 1;
}

.user-name {
  overflow: hidden;
  color: #ffffff;
  font-size: 13px;
  font-weight: 750;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-role {
  color: var(--text-muted);
  font-size: 11px;
  font-weight: 650;
}

.logout-btn {
  width: 100%;
  justify-content: flex-start;
  color: var(--text-secondary);
}

@media (max-width: 900px) {
  .sidebar {
    width: 100%;
    height: auto;
    min-height: 0;
    border-right: 0;
    border-bottom: 1px solid rgba(126, 211, 255, 0.18);
  }

  .sidebar-header,
  .sidebar-footer {
    display: none;
  }

  .sidebar-nav {
    flex-direction: row;
    overflow-x: auto;
    padding: 10px;
  }

  .nav-item {
    flex: 0 0 auto;
  }
}
</style>

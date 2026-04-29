<template>
  <div class="app-layout">
    <Sidebar />
    <div class="main-content">
      <Header :page-title="pageTitle" />
      <main class="page-content">
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue';
import { useRoute } from 'vue-router';
import { useDeviceStore } from '@/store';
import Sidebar from './Sidebar.vue';
import Header from './Header.vue';

const route = useRoute();
const deviceStore = useDeviceStore();

const pageTitle = computed(() => {
  const routeName = route.name as string;
  const titleMap: Record<string, string> = {
    Dashboard: '监控面板',
    History: '历史记录',
    Devices: '设备管理',
    Tasks: '任务管理',
    Users: '用户管理'
  };
  return titleMap[routeName] || '监控面板';
});

onMounted(() => {
  deviceStore.startAutoRefresh();
});

onUnmounted(() => {
  deviceStore.stopAutoRefresh();
});
</script>

<style scoped>
.app-layout {
  @apply flex h-screen bg-gray-50;
}

.main-content {
  @apply flex-1 flex flex-col overflow-hidden;
}

.page-content {
  @apply flex-1 overflow-auto p-6;
}
</style>
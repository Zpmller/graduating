<template>
  <div class="app-layout">
    <ParticleBackdrop />
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
import ParticleBackdrop from '@/components/common/ParticleBackdrop.vue';
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
  position: relative;
  display: flex;
  height: 100vh;
  overflow: hidden;
  background: var(--mine-bg-deep);
}

.main-content {
  position: relative;
  z-index: 1;
  display: flex;
  flex: 1;
  min-width: 0;
  flex-direction: column;
  overflow: hidden;
}

.page-content {
  position: relative;
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 18px;
}

.page-content::-webkit-scrollbar {
  width: 10px;
}

.page-content::-webkit-scrollbar-thumb {
  border: 2px solid rgba(2, 8, 18, 0.7);
  border-radius: 999px;
  background: rgba(93, 198, 235, 0.32);
}

@media (max-width: 900px) {
  .app-layout {
    display: block;
    overflow: auto;
  }

  .main-content {
    min-height: 100vh;
  }

  .page-content {
    padding: 12px;
  }
}
</style>

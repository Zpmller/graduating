<template>
  <AppLayout>
    <div class="dashboard">
      <!-- 顶部状态栏 -->
      <div class="dashboard-toolbar">
        <div class="stats-row">
          <span class="stat-pill stat-alerts">
            <el-icon><WarningFilled /></el-icon>
            {{ alertStore.criticalAlertCount }} 紧急
          </span>
          <span class="stat-pill stat-warning">
            <el-icon><Warning /></el-icon>
            {{ alertStore.alertCount }} 警报
          </span>
          <span class="stat-pill stat-online">
            <el-icon><CircleCheck /></el-icon>
            {{ deviceStore.onlineDevices.length }}/{{ deviceStore.devices.length }} 在线
          </span>
          <span class="stat-pill stat-tasks">
            <el-icon><Tickets /></el-icon>
            {{ taskStore.pendingTasks.length }} 待办
          </span>
        </div>
        <div class="toolbar-actions">
          <el-button size="small" @click="refreshAll">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </div>

      <!-- 视频墙 -->
      <div class="video-wall">
        <div
          v-for="(slot, index) in wallSlots"
          :key="slot?.id ?? `empty-${index}`"
          class="video-wall-cell"
        >
          <StreamWallCell :device="slot" />
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue';
import {
  Warning,
  WarningFilled,
  CircleCheck,
  Tickets,
  Refresh
} from '@element-plus/icons-vue';
import AppLayout from '@/components/layout/AppLayout.vue';
import StreamWallCell from '@/components/video/StreamWallCell.vue';
import { useAlertStore, useDeviceStore, useTaskStore, useStreamStore } from '@/store';
import type { Device } from '@/types';

const WALL_COLS = 4;
const WALL_ROWS = 3;
const WALL_SIZE = WALL_COLS * WALL_ROWS;

const alertStore = useAlertStore();
const deviceStore = useDeviceStore();
const taskStore = useTaskStore();
const streamStore = useStreamStore();

/** 有视频流地址的设备（用于墙格） */
const devicesWithStream = computed(() =>
  deviceStore.devices.filter((d: Device) => d.ip_address?.trim())
);

/** 墙格槽位：前 N 个为设备，其余为 null 显示 NO SIGNAL */
const wallSlots = computed(() => {
  const list: (Device | null)[] = [];
  for (let i = 0; i < WALL_SIZE; i++) {
    list.push(devicesWithStream.value[i] ?? null);
  }
  return list;
});

const refreshAll = async () => {
  await Promise.all([
    alertStore.fetchActiveAlerts(),
    alertStore.fetchStats(),
    deviceStore.fetchDevices(),
    taskStore.fetchTasks()
  ]);
};

onMounted(async () => {
  await Promise.all([
    alertStore.fetchActiveAlerts(),
    alertStore.fetchStats(),
    deviceStore.fetchDevices(),
    taskStore.fetchTasks()
  ]);
  alertStore.startPolling();
});

onUnmounted(() => {
  alertStore.stopPolling();
  streamStore.stopAllStreams().catch(() => {});
});
</script>

<style scoped>
.dashboard {
  @apply flex flex-col h-full min-h-0 bg-neutral-950;
}

.dashboard-toolbar {
  @apply flex-shrink-0 flex items-center justify-between px-4 py-2 bg-neutral-900 border-b border-neutral-800;
}

.stats-row {
  @apply flex items-center gap-3 flex-wrap;
}

.stat-pill {
  @apply inline-flex items-center gap-1.5 px-3 py-1 rounded text-sm;
}

.stat-alerts {
  @apply bg-red-900/50 text-red-300 border border-red-700/50;
}

.stat-warning {
  @apply bg-amber-900/50 text-amber-300 border border-amber-700/50;
}

.stat-online {
  @apply bg-emerald-900/50 text-emerald-300 border border-emerald-700/50;
}

.stat-tasks {
  @apply bg-blue-900/50 text-blue-300 border border-blue-700/50;
}

.toolbar-actions {
  @apply flex items-center gap-2;
}

.video-wall {
  @apply flex-1 p-3 overflow-auto;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  grid-template-rows: repeat(3, minmax(180px, 1fr));
  gap: 8px;
}

.video-wall-cell {
  @apply min-h-0 rounded overflow-hidden;
}
</style>

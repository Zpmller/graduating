<template>
  <AppLayout>
    <div class="dashboard mine-page">
      <div class="dashboard-toolbar glass-panel">
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
        <div class="toolbar-actions page-actions">
          <el-button size="small" @click="refreshAll">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </div>

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
  display: flex;
  height: 100%;
  min-height: 0;
  flex-direction: column;
  gap: 12px;
}

.dashboard-toolbar {
  flex-shrink: 0;
}

.stats-row {
  display: grid;
  flex: 1;
  grid-template-columns: repeat(4, minmax(136px, 1fr));
  gap: 10px;
}

.stat-pill {
  position: relative;
  display: inline-flex;
  min-height: 54px;
  align-items: center;
  gap: 9px;
  padding: 10px 14px;
  overflow: hidden;
  border: 1px solid rgba(126, 211, 255, 0.16);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.04);
  font-size: 15px;
  font-weight: 780;
  line-height: 1;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.08);
}

.stat-pill::after {
  position: absolute;
  inset: auto 10px 0;
  height: 1px;
  content: '';
  background: currentColor;
  opacity: 0.38;
  box-shadow: 0 0 14px currentColor;
}

.stat-pill .el-icon {
  font-size: 20px;
}

.stat-alerts {
  color: #ff8fa1;
  border-color: rgba(255, 77, 104, 0.36);
  background: rgba(255, 77, 104, 0.1);
}

.stat-warning {
  color: #ffd17a;
  border-color: rgba(255, 186, 58, 0.34);
  background: rgba(255, 186, 58, 0.1);
}

.stat-online {
  color: #80f0bd;
  border-color: rgba(57, 231, 159, 0.34);
  background: rgba(57, 231, 159, 0.1);
}

.stat-tasks {
  color: #8edcff;
  border-color: rgba(28, 199, 255, 0.34);
  background: rgba(28, 199, 255, 0.1);
}

.toolbar-actions {
  justify-content: flex-end;
}

.video-wall {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 3px;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  grid-template-rows: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.video-wall-cell {
  min-height: 0;
  overflow: hidden;
  border-radius: 8px;
}

@media (max-width: 1200px) {
  .stats-row {
    grid-template-columns: repeat(2, minmax(136px, 1fr));
  }

  .video-wall {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    grid-template-rows: repeat(6, minmax(170px, 1fr));
  }
}

@media (max-width: 720px) {
  .dashboard {
    height: auto;
  }

  .stats-row,
  .video-wall {
    grid-template-columns: 1fr;
  }

  .video-wall {
    grid-template-rows: none;
  }

  .video-wall-cell {
    min-height: 190px;
  }
}
</style>

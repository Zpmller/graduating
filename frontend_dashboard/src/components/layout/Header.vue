<template>
  <header class="header">
    <div class="header-content">
      <div class="header-left">
        <h1 class="page-title">{{ pageTitle }}</h1>
      </div>

      <div class="header-right">
        <div class="status-indicators">
          <div class="status-item">
            <el-badge :value="criticalAlertCount" :max="99" class="critical-badge">
              <el-button type="danger" size="small" plain>
                <el-icon><Warning /></el-icon>
                紧急警报
              </el-button>
            </el-badge>
          </div>

          <div class="status-item">
            <el-badge :value="onlineDeviceCount" class="online-badge">
              <el-button type="success" size="small" plain>
                <el-icon><CircleCheck /></el-icon>
                在线设备
              </el-button>
            </el-badge>
          </div>
        </div>

        <div class="time-display">
          {{ currentTime }}
        </div>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { Warning, CircleCheck } from '@element-plus/icons-vue';
import { useAlertStore, useDeviceStore } from '@/store';

interface Props {
  pageTitle?: string;
}

const props = withDefaults(defineProps<Props>(), {
  pageTitle: '监控面板'
});

const currentTime = ref('');
let timeInterval: number | null = null;

const alertStore = useAlertStore();
const deviceStore = useDeviceStore();

const criticalAlertCount = computed(() => alertStore.criticalAlertCount);
const onlineDeviceCount = computed(() => deviceStore.onlineDevices.length);

const updateTime = () => {
  currentTime.value = new Date().toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  });
};

onMounted(() => {
  updateTime();
  timeInterval = window.setInterval(updateTime, 1000);
});

onUnmounted(() => {
  if (timeInterval) {
    clearInterval(timeInterval);
  }
});
</script>

<style scoped>
.header {
  @apply bg-white border-b border-gray-200 px-6 py-4;
}

.header-content {
  @apply flex items-center justify-between;
}

.header-left {
  @apply flex items-center;
}

.page-title {
  @apply text-2xl font-bold text-gray-800;
}

.header-right {
  @apply flex items-center space-x-6;
}

.status-indicators {
  @apply flex items-center space-x-4;
}

.status-item {
  @apply flex items-center;
}

.critical-badge :deep(.el-badge__content) {
  @apply bg-red-500;
}

.online-badge :deep(.el-badge__content) {
  @apply bg-green-500;
}

.time-display {
  @apply text-sm text-gray-600 font-mono;
}
</style>
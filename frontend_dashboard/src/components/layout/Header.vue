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
  position: relative;
  z-index: 2;
  padding: 14px 18px 0;
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-height: 64px;
  padding: 0 18px;
  border: 1px solid rgba(126, 211, 255, 0.18);
  border-radius: 8px;
  background:
    linear-gradient(145deg, rgba(255, 255, 255, 0.07), rgba(255, 255, 255, 0.018)),
    rgba(6, 23, 38, 0.72);
  box-shadow: 0 12px 34px rgba(0, 0, 0, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(18px) saturate(130%);
}

.header-left {
  display: flex;
  align-items: center;
  min-width: 0;
}

.page-title {
  margin: 0;
  color: #ffffff;
  font-size: 22px;
  font-weight: 850;
  line-height: 1.1;
  letter-spacing: 0;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 18px;
}

.status-indicators {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-item {
  display: flex;
  align-items: center;
}

.status-item :deep(.el-button) {
  min-height: 34px;
  padding-inline: 12px;
}

.critical-badge :deep(.el-badge__content) {
  border: 0;
  background: var(--accent-red);
  box-shadow: 0 0 16px rgba(255, 77, 104, 0.45);
}

.online-badge :deep(.el-badge__content) {
  border: 0;
  background: var(--accent-emerald);
  color: #032014;
  box-shadow: 0 0 16px rgba(57, 231, 159, 0.42);
}

.time-display {
  padding: 8px 10px;
  border: 1px solid rgba(126, 211, 255, 0.16);
  border-radius: 6px;
  color: #bde6ff;
  background: rgba(2, 12, 22, 0.45);
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', monospace;
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
}

@media (max-width: 900px) {
  .header {
    padding: 10px 12px 0;
  }

  .header-content,
  .header-right,
  .status-indicators {
    align-items: stretch;
    flex-direction: column;
  }

  .header-content {
    padding: 14px;
  }
}
</style>

<template>
  <div class="stream-wall-cell">
    <div class="cell-inner">
      <!-- 有设备且可拉流：显示视频或加载/失败 -->
      <template v-if="device && hasStreamUrl">
        <video
          v-show="connectionState === 'connected'"
          ref="videoEl"
          class="cell-video"
          autoplay
          muted
          playsinline
        />
        <div
          v-if="connectionState === 'connecting' || connectionState === 'disconnected'"
          class="cell-placeholder cell-loading"
        >
          <el-icon class="placeholder-icon"><Loading /></el-icon>
          <span>连接中...</span>
        </div>
        <div
          v-else-if="connectionState === 'failed'"
          class="cell-placeholder cell-error"
        >
          <el-icon class="placeholder-icon"><VideoPause /></el-icon>
          <span>连接失败</span>
        </div>
      </template>
      <!-- 无设备或无流地址：NO SIGNAL -->
      <div
        v-else
        class="cell-placeholder cell-no-signal"
      >
        <span class="no-signal-text">NO SIGNAL</span>
      </div>

      <!-- 底部标签：设备名 + 时间 -->
      <div class="cell-label">
        <span class="cell-name">{{ device?.name || 'NO SIGNAL' }}</span>
        <span class="cell-time">{{ currentTime }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { Loading, VideoPause } from '@element-plus/icons-vue';
import type { Device } from '@/types';
import { useStreamStore } from '@/store';
import { WebRTCStreamManager } from '@/utils/webrtc';

const props = defineProps<{
  device: Device | null;
}>();

const streamStore = useStreamStore();
const videoEl = ref<HTMLVideoElement>();
const webRTCManager = ref<WebRTCStreamManager>();
const currentTime = ref('');
let timeTimer: ReturnType<typeof setInterval> | null = null;

const hasStreamUrl = computed(() =>
  Boolean(props.device?.ip_address?.trim())
);

const connectionState = computed(() => {
  if (!props.device) return 'disconnected';
  return streamStore.getStreamStatus(props.device.id)?.connection_state ?? 'disconnected';
});

function updateTime() {
  const now = new Date();
  currentTime.value = now.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  }).replace(/\//g, '-');
}

onMounted(async () => {
  updateTime();
  timeTimer = setInterval(updateTime, 1000);

  if (!props.device?.id || !hasStreamUrl.value) return;

  try {
    const result = await streamStore.startStream(props.device.id, 'medium');
    const offer = result?.offer;
    if (offer && videoEl.value) {
      webRTCManager.value = new WebRTCStreamManager(videoEl.value);
      await webRTCManager.value.startStream(offer);
      streamStore.updateStreamStatus(props.device.id, { connection_state: 'connected' });
    }
  } catch (e: any) {
    const msg = e?.detail || e?.message || '连接失败';
    console.error('StreamWallCell start failed:', msg, e);
    streamStore.updateStreamStatus(props.device.id, {
      connection_state: 'failed',
      error: msg
    });
  }
});

onUnmounted(() => {
  if (timeTimer) clearInterval(timeTimer);
  webRTCManager.value?.stopStream();
  if (props.device?.id) {
    streamStore.stopStream(props.device.id).catch(() => {});
  }
});
</script>

<style scoped>
.stream-wall-cell {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 160px;
  overflow: hidden;
  border: 1px solid rgba(126, 211, 255, 0.18);
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.86);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.04), 0 14px 30px rgba(0, 0, 0, 0.22);
}

.stream-wall-cell::before {
  position: absolute;
  inset: 0;
  z-index: 2;
  pointer-events: none;
  content: '';
  background:
    linear-gradient(90deg, rgba(255, 255, 255, 0.035) 1px, transparent 1px),
    linear-gradient(rgba(255, 255, 255, 0.026) 1px, transparent 1px);
  background-size: 42px 42px;
  opacity: 0.28;
}

.cell-inner {
  position: relative;
  display: flex;
  width: 100%;
  height: 100%;
  align-items: center;
  justify-content: center;
}

.cell-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.cell-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: rgba(168, 196, 216, 0.62);
}

.cell-loading {
  color: #80e8ff;
}

.cell-error {
  color: #ffd17a;
}

.cell-no-signal {
  background:
    linear-gradient(135deg, rgba(6, 21, 34, 0.92), rgba(1, 8, 14, 0.96)),
    repeating-linear-gradient(0deg, rgba(255, 255, 255, 0.025) 0 1px, transparent 1px 5px);
  color: rgba(117, 143, 160, 0.68);
}

.no-signal-text {
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', monospace;
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 0.14em;
}

.placeholder-icon {
  margin-bottom: 5px;
  font-size: 26px;
}

.cell-label {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  z-index: 3;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 8px 10px;
  border-top: 1px solid rgba(126, 211, 255, 0.16);
  color: #ffffff;
  background: linear-gradient(180deg, rgba(3, 12, 23, 0.45), rgba(3, 12, 23, 0.86));
  font-size: 12px;
  backdrop-filter: blur(12px);
}

.cell-name {
  max-width: 68%;
  overflow: hidden;
  font-weight: 800;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cell-time {
  color: var(--text-muted);
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', monospace;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
</style>

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
          <span>{{ streamStore.getStreamStatus(props.device?.id ?? 0)?.error || '连接失败' }}</span>
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
        <span class="cell-name">{{ device?.name || '未命名' }}</span>
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
  @apply aspect-video bg-black rounded overflow-hidden border border-gray-800;
}

.cell-inner {
  @apply relative w-full h-full flex items-center justify-center;
}

.cell-video {
  @apply w-full h-full object-cover;
}

.cell-placeholder {
  @apply absolute inset-0 flex flex-col items-center justify-center text-gray-500;
}

.cell-loading {
  @apply text-blue-400;
}

.cell-error {
  @apply text-amber-500;
}

.cell-no-signal {
  @apply bg-neutral-900 text-neutral-600;
}

.no-signal-text {
  @apply text-sm font-mono tracking-widest;
}

.placeholder-icon {
  @apply text-2xl mb-1;
}

.cell-label {
  @apply absolute bottom-0 left-0 right-0 px-2 py-1 bg-black/70 text-white text-xs flex justify-between items-center;
}

.cell-name {
  @apply truncate max-w-[70%];
}

.cell-time {
  @apply text-gray-400 tabular-nums;
}
</style>

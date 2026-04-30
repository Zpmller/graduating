<template>
  <div class="video-player">
    <div class="video-container">
      <video
        ref="videoElement"
        class="video-element"
        autoplay
        muted
        playsinline
      ></video>

      <!-- Video Controls -->
      <div class="video-controls">
        <div class="control-group">
          <el-button
            link
            type="primary"
            size="small"
            @click="toggleDetectionOverlay"
            :loading="loading"
          >
            <el-icon>
              <component :is="detectionOverlayEnabled ? Hide : View" />
            </el-icon>
            {{ detectionOverlayEnabled ? '隐藏检测' : '显示检测' }}
          </el-button>

          <el-select
            v-model="quality"
            size="small"
            class="quality-select"
            @change="changeQuality"
            :disabled="loading"
          >
            <el-option label="低质量" value="low" />
            <el-option label="中等质量" value="medium" />
            <el-option label="高质量" value="high" />
          </el-select>
        </div>

        <div class="control-group">
          <el-button type="danger" size="small" @click="$emit('close')">
            <el-icon><Close /></el-icon>
            关闭
          </el-button>
        </div>
      </div>

      <!-- Connection Status -->
      <div v-if="connectionStatus !== 'connected'" class="connection-status">
        <el-alert
          :type="getStatusType(connectionStatus)"
          :title="getStatusMessage(connectionStatus)"
          :description="error"
          show-icon
          :closable="false"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed } from 'vue';
import { ElMessage } from 'element-plus';
import { Close, Hide, View } from '@element-plus/icons-vue';
import type { Device } from '@/types';
import { useStreamStore } from '@/store';
import { WebRTCStreamManager } from '@/utils/webrtc';

interface Props {
  device: Device;
}

const props = defineProps<Props>();

defineEmits<{
  close: [];
}>();

const streamStore = useStreamStore();
const videoElement = ref<HTMLVideoElement>();
const webRTCManager = ref<WebRTCStreamManager>();
const loading = ref(false);
const hasStartedRef = ref(false);
const quality = ref<'low' | 'medium' | 'high'>('medium');
const detectionOverlayEnabled = computed(
  () => streamStore.getStreamStatus(props.device.id)?.detection_overlay_enabled ?? true
);

const connectionStatus = computed(() => {
  const status = streamStore.activeStreams.get(props.device.id);
  return status?.connection_state || 'disconnected';
});

const error = computed(() => {
  const status = streamStore.activeStreams.get(props.device.id);
  return status?.error || '';
});

const getStatusType = (status: string) => {
  const typeMap = {
    connecting: 'info',
    connected: 'success',
    disconnected: 'warning',
    failed: 'error'
  };
  return typeMap[status as keyof typeof typeMap] || 'info';
};

const getStatusMessage = (status: string) => {
  const messageMap = {
    connecting: '连接中',
    connected: '已连接',
    disconnected: '已断开',
    failed: '连接失败'
  };
  return messageMap[status as keyof typeof messageMap] || status;
};

const toggleDetectionOverlay = async () => {
  loading.value = true;
  try {
    await streamStore.toggleDetectionOverlay(props.device.id);
  } catch {
    ElMessage.error('切换检测覆盖失败');
  } finally {
    loading.value = false;
  }
};

const changeQuality = async () => {
  loading.value = true;
  try {
    await streamStore.setStreamQuality(props.device.id, quality.value);
  } catch (error) {
    ElMessage.error('切换质量失败');
  } finally {
    loading.value = false;
  }
};

// Initialize WebRTC when stream is started（仅启动一次，避免 updateStreamStatus 触发 watch 导致循环）
watch(
  () => [streamStore.isStreaming(props.device.id), videoElement.value] as const,
  async ([isStreaming, el]) => {
    if (!isStreaming || !el || hasStartedRef.value) return;
    hasStartedRef.value = true;

    webRTCManager.value = new WebRTCStreamManager(el);

    try {
      const status = streamStore.getStreamStatus(props.device.id);
      const toUse = status?.offer ?? (await streamStore.startStream(props.device.id, quality.value))?.offer;
      if (toUse) {
        await webRTCManager.value.startStream(toUse);
        streamStore.updateStreamStatus(props.device.id, {
          connection_state: 'connected'
        });
      }
    } catch (error) {
      console.error('Failed to start WebRTC stream:', error);
      streamStore.updateStreamStatus(props.device.id, {
        connection_state: 'failed',
        error: (error as Error)?.message || 'WebRTC连接失败'
      });
    }
  },
  { immediate: true }
);

onUnmounted(() => {
  if (webRTCManager.value) {
    webRTCManager.value.stopStream();
  }
});
</script>

<style scoped>
.video-player {
  position: relative;
}

.video-container {
  position: relative;
  overflow: hidden;
  border: 1px solid rgba(126, 211, 255, 0.22);
  border-radius: 8px;
  background: #000;
  box-shadow: 0 18px 44px rgba(0, 0, 0, 0.32);
}

.video-element {
  width: 100%;
  height: auto;
  max-height: 64vh;
}

.video-controls {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px;
  border-top: 1px solid rgba(126, 211, 255, 0.18);
  background: rgba(2, 10, 18, 0.78);
  backdrop-filter: blur(14px);
}

.control-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.quality-select {
  width: 128px;
}

.connection-status {
  position: absolute;
  top: 14px;
  right: 14px;
  left: 14px;
}
</style>

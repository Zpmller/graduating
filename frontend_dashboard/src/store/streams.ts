import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type { StreamStatus, StreamControlParams } from '@/types';
import { streamApi } from '@/api';

export const useStreamStore = defineStore('streams', () => {
  // State
  const activeStreams = ref<Map<number, StreamStatus>>(new Map());
  const loading = ref(false);
  const error = ref<string | null>(null);

  // Getters
  const isStreaming = computed(() => (deviceId: number) => {
    const status = activeStreams.value.get(deviceId);
    return status?.is_active || false;
  });

  const streamCount = computed(() => activeStreams.value.size);

  const activeStreamIds = computed(() =>
    Array.from(activeStreams.value.keys())
  );

  const getStreamStatus = computed(() => (deviceId: number) =>
    activeStreams.value.get(deviceId)
  );

  // Actions
  const startStream = async (deviceId: number, quality: 'low' | 'medium' | 'high' = 'medium') => {
    loading.value = true;
    error.value = null;

    try {
      const offer = await streamApi.getStreamOffer(deviceId, quality);

      // Initialize stream status（含 offer 供组件直接使用，避免重复请求）
      const initialStatus: StreamStatus = {
        device_id: deviceId,
        is_active: true,
        quality,
        detection_overlay_enabled: true,
        connection_state: 'connecting',
        offer,
      };

      activeStreams.value.set(deviceId, initialStatus);

      return { offer, initialStatus };
    } catch (err: any) {
      error.value = err.detail || '启动视频流失败';
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const stopStream = async (deviceId: number) => {
    try {
      const status = activeStreams.value.get(deviceId);
      if (status?.stream_id) {
        await streamApi.stopStream(deviceId, status.stream_id);
      }

      activeStreams.value.delete(deviceId);
    } catch (err: any) {
      error.value = err.detail || '停止视频流失败';
      throw err;
    }
  };

  const updateStreamStatus = (deviceId: number, status: Partial<StreamStatus>) => {
    const currentStatus = activeStreams.value.get(deviceId);
    activeStreams.value.set(deviceId, {
      device_id: deviceId,
      ...currentStatus,
      ...status,
    } as StreamStatus);
  };

  const toggleDetectionOverlay = async (deviceId: number) => {
    try {
      const status = activeStreams.value.get(deviceId);
      if (!status) return;

      const newEnabled = !status.detection_overlay_enabled;

      await streamApi.controlStream(deviceId, {
        device_id: deviceId,
        action: 'toggle_overlay',
        enable_overlay: newEnabled,
      });

      updateStreamStatus(deviceId, { detection_overlay_enabled: newEnabled });
    } catch (err: any) {
      error.value = err.detail || '切换检测覆盖失败';
      throw err;
    }
  };

  const setStreamQuality = async (deviceId: number, quality: 'low' | 'medium' | 'high') => {
    try {
      await streamApi.controlStream(deviceId, {
        device_id: deviceId,
        action: 'set_quality',
        quality,
      });

      updateStreamStatus(deviceId, { quality });
    } catch (err: any) {
      error.value = err.detail || '设置视频质量失败';
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const fetchStreamStatus = async (deviceId: number) => {
    try {
      const status = await streamApi.getStreamStatus(deviceId);
      activeStreams.value.set(deviceId, status);
      return status;
    } catch (err: any) {
      error.value = err.detail || '获取流状态失败';
      throw err;
    }
  };

  const stopAllStreams = async () => {
    const promises = Array.from(activeStreams.value.keys()).map(deviceId =>
      stopStream(deviceId).catch(err => {
        console.error(`Failed to stop stream for device ${deviceId}:`, err);
      })
    );

    await Promise.all(promises);
    activeStreams.value.clear();
  };

  return {
    // State
    activeStreams,
    loading,
    error,

    // Getters
    isStreaming,
    streamCount,
    activeStreamIds,
    getStreamStatus,

    // Actions
    startStream,
    stopStream,
    updateStreamStatus,
    toggleDetectionOverlay,
    setStreamQuality,
    fetchStreamStatus,
    stopAllStreams,
  };
});
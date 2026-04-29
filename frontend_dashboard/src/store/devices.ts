import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type { Device, CreateDeviceParams } from '@/types';
import { deviceApi } from '@/api';

/** 设备列表轮询间隔（毫秒），用于自动刷新在线状态与视频流信息 */
const DEVICE_REFRESH_INTERVAL = 30000;

/** 规范化设备状态：后端可能返回 ONLINE/online，统一为小写 */
function normalizeDeviceStatus(s: unknown): 'online' | 'offline' | 'maintenance' {
  const v = typeof s === 'string' ? s.toLowerCase() : 'offline';
  if (v === 'online' || v === 'offline' || v === 'maintenance') return v;
  return 'offline';
}

function normalizeDevice(d: Record<string, unknown>): Device {
  const status = normalizeDeviceStatus(d.status);
  return { ...d, status } as Device;
}

export const useDeviceStore = defineStore('devices', () => {
  // State
  const devices = ref<Device[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);
  let _refreshTimer: ReturnType<typeof setInterval> | null = null;

  // Getters
  const onlineDevices = computed(() =>
    devices.value.filter(device => (device.status || '').toLowerCase() === 'online')
  );

  const offlineDevices = computed(() =>
    devices.value.filter(device => (device.status || '').toLowerCase() === 'offline')
  );

  const maintenanceDevices = computed(() =>
    devices.value.filter(device => (device.status || '').toLowerCase() === 'maintenance')
  );

  const getDeviceById = computed(() => (id: number) =>
    devices.value.find(device => device.id === id)
  );

  // Actions
  const fetchDevices = async (options?: { includeStreamStatus?: boolean }) => {
    loading.value = true;
    error.value = null;

    try {
      const response = await deviceApi.getAll({
        include_stream_status: options?.includeStreamStatus ?? true
      });
      devices.value = (response.items || []).map(normalizeDevice);
    } catch (err: any) {
      error.value = err.detail || '获取设备列表失败';
    } finally {
      loading.value = false;
    }
  };

  /** 启动定时刷新设备列表（在线状态、视频流信息） */
  const startAutoRefresh = () => {
    if (_refreshTimer) return;
    _refreshTimer = setInterval(() => {
      fetchDevices({ includeStreamStatus: true });
    }, DEVICE_REFRESH_INTERVAL);
  };

  /** 停止定时刷新 */
  const stopAutoRefresh = () => {
    if (_refreshTimer) {
      clearInterval(_refreshTimer);
      _refreshTimer = null;
    }
  };

  const createDevice = async (data: CreateDeviceParams) => {
    loading.value = true;
    error.value = null;

    try {
      const newDevice = await deviceApi.create(data);
      devices.value.push(normalizeDevice(newDevice as Record<string, unknown>));
      return newDevice;
    } catch (err: any) {
      error.value = err.detail || '创建设备失败';
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const updateDevice = async (id: number, data: Partial<CreateDeviceParams>) => {
    loading.value = true;
    error.value = null;

    try {
      const updatedDevice = await deviceApi.update(id, data);
      const index = devices.value.findIndex(device => device.id === id);
      if (index !== -1) {
        devices.value[index] = normalizeDevice(updatedDevice as Record<string, unknown>);
      }
      return updatedDevice;
    } catch (err: any) {
      error.value = err.detail || '更新设备失败';
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const deleteDevice = async (id: number) => {
    loading.value = true;
    error.value = null;

    try {
      await deviceApi.delete(id);
      devices.value = devices.value.filter(device => device.id !== id);
    } catch (err: any) {
      error.value = err.detail || '删除设备失败';
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const getCalibrationConfig = async (id: number) => {
    try {
      return await deviceApi.getCalibrationConfig(id);
    } catch (err: any) {
      error.value = err.detail || '获取校准配置失败';
      throw err;
    }
  };

  const uploadCalibrationConfig = async (id: number, file: File) => {
    try {
      return await deviceApi.uploadCalibrationConfig(id, file);
    } catch (err: any) {
      error.value = err.detail || '上传校准配置失败';
      throw err;
    }
  };

  const uploadCalibrationImages = async (id: number, files: File[]) => {
    try {
      return await deviceApi.uploadCalibrationImages(id, files);
    } catch (err: any) {
      error.value = err.detail || '上传校准图片失败';
      throw err;
    }
  };

  return {
    // State
    devices,
    loading,
    error,

    // Getters
    onlineDevices,
    offlineDevices,
    maintenanceDevices,
    getDeviceById,

    // Actions
    fetchDevices,
    startAutoRefresh,
    stopAutoRefresh,
    createDevice,
    updateDevice,
    deleteDevice,
    getCalibrationConfig,
    uploadCalibrationConfig,
    uploadCalibrationImages,
  };
});
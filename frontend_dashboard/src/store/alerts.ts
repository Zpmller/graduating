import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type { Alert, AlertFilterParams, AlertStats } from '@/types';
import { alertApi } from '@/api';

export const useAlertStore = defineStore('alerts', () => {
  // State
  const activeAlerts = ref<Alert[]>([]);
  const historicalAlerts = ref<Alert[]>([]);
  const stats = ref<AlertStats | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const pollingActive = ref(false);

  // Getters
  const criticalAlerts = computed(() =>
    activeAlerts.value.filter(alert => alert.severity === 'CRITICAL')
  );

  const unacknowledgedAlerts = computed(() =>
    activeAlerts.value.filter(alert => !alert.is_acknowledged)
  );

  const alertCount = computed(() => activeAlerts.value.length);

  const criticalAlertCount = computed(() => criticalAlerts.value.length);

  // Actions
  const fetchActiveAlerts = async () => {
    try {
      const response = await alertApi.getAll({
        is_acknowledged: false,
        limit: 100
      });
      activeAlerts.value = response.items;
    } catch (err: any) {
      error.value = err.detail || '获取活跃警报失败';
    }
  };

  const fetchHistoricalAlerts = async (params?: AlertFilterParams) => {
    loading.value = true;
    error.value = null;

    try {
      // 不默认按 is_acknowledged 筛选，历史记录显示全部告警（含未确认的新告警）
      const response = await alertApi.getAll({
        limit: 100,
        ...params
      });
      historicalAlerts.value = response.items;
    } catch (err: any) {
      error.value = err.detail || '获取历史警报失败';
    } finally {
      loading.value = false;
    }
  };

  const fetchStats = async (params?: { start_date?: string; end_date?: string }) => {
    try {
      stats.value = await alertApi.getStats(params);
    } catch (err: any) {
      error.value = err.detail || '获取统计数据失败';
    }
  };

  const acknowledgeAlert = async (id: number, notes?: string) => {
    try {
      const updatedAlert = await alertApi.acknowledge(id, notes);

      // Update in active alerts
      const activeIndex = activeAlerts.value.findIndex(alert => alert.id === id);
      if (activeIndex !== -1) {
        activeAlerts.value.splice(activeIndex, 1);
      }

      // Add to historical alerts
      historicalAlerts.value.unshift(updatedAlert);

      return updatedAlert;
    } catch (err: any) {
      error.value = err.detail || '确认警报失败';
      throw err;
    }
  };

  const pollActiveAlerts = async () => {
    if (!pollingActive.value) return;

    await fetchActiveAlerts();
    await fetchStats();

    // Continue polling if still active
    if (pollingActive.value) {
      setTimeout(pollActiveAlerts, 3000);
    }
  };

  const startPolling = () => {
    pollingActive.value = true;
    pollActiveAlerts();
  };

  const stopPolling = () => {
    pollingActive.value = false;
  };

  return {
    // State
    activeAlerts,
    historicalAlerts,
    stats,
    loading,
    error,
    pollingActive,

    // Getters
    criticalAlerts,
    unacknowledgedAlerts,
    alertCount,
    criticalAlertCount,

    // Actions
    fetchActiveAlerts,
    fetchHistoricalAlerts,
    fetchStats,
    acknowledgeAlert,
    startPolling,
    stopPolling,
  };
});
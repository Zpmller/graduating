<template>
  <AppLayout>
    <div class="devices-view mine-page">
      <div class="header-actions glass-panel glass-toolbar">
        <el-button type="primary" @click="showCreateDialog = true">
          <el-icon><Plus /></el-icon>
          添加设备
        </el-button>
        <el-button @click="openAddLocalCamera">
          <el-icon><VideoPlay /></el-icon>
          添加本机摄像头
        </el-button>
        <el-button @click="fetchDevices">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>

      <div v-if="deviceStore.loading" class="loading-container glass-panel">
        <LoadingSpinner text="加载设备中..." />
      </div>

      <div v-else-if="deviceStore.devices.length === 0" class="empty-container glass-panel">
        <EmptyState
          description="暂无设备"
          action-text="添加设备"
          :action-handler="() => showCreateDialog = true"
        />
      </div>

      <div v-else class="devices-grid">
        <div
          v-for="device in deviceStore.devices"
          :key="device.id"
          class="device-card glass-panel"
          :class="`device-card--${(device.status || 'offline').toLowerCase()}`"
        >
          <div class="device-header">
            <div class="device-status">
              <el-icon :class="`status-icon status-icon--${device.status}`">
                <component :is="getStatusIcon(device.status)" />
              </el-icon>
              <span class="status-text">{{ getStatusLabel(device.status) }}</span>
            </div>
            <el-dropdown @command="handleDeviceAction">
              <el-button link type="primary" size="small">
                <el-icon><More /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item :command="{ action: 'edit', device }">
                    <el-icon><Edit /></el-icon>
                    编辑
                  </el-dropdown-item>
                  <el-dropdown-item :command="{ action: 'calibrate', device }">
                    <el-icon><Setting /></el-icon>
                    校准
                  </el-dropdown-item>
                  <el-dropdown-item
                    :command="{ action: 'stream', device }"
                    :disabled="!device.ip_address || !device.ip_address.trim()"
                  >
                    <el-icon><VideoPlay /></el-icon>
                    视频流
                  </el-dropdown-item>
                  <el-dropdown-item :command="{ action: 'delete', device }" divided>
                    <el-icon><Delete /></el-icon>
                    删除
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>

          <div class="device-content">
            <h3 class="device-name">{{ device.name }}</h3>
            <p class="device-location">{{ device.location }}</p>
            <div class="device-ip">视频源: {{ device.ip_address }}</div>
            <div v-if="device.edge_host" class="device-edge-host">Edge: {{ device.edge_host }}</div>
            <div v-if="device.last_heartbeat" class="device-heartbeat">
              最后心跳: {{ formatTime(device.last_heartbeat) }}
            </div>
            <el-tag v-if="device.stream_status?.is_active" type="success" size="small" class="stream-tag">
              视频推流中
            </el-tag>
          </div>
        </div>
      </div>

      <!-- Create/Edit Device Dialog -->
      <el-dialog
        v-model="showCreateDialog"
        :title="editingDevice ? '编辑设备' : '添加设备'"
        width="500px"
      >
        <el-form
          ref="deviceFormRef"
          :model="deviceForm"
          :rules="deviceRules"
          label-width="80px"
        >
          <el-form-item label="设备名称" prop="name">
            <el-input v-model="deviceForm.name" placeholder="输入设备名称" />
          </el-form-item>

          <el-form-item label="位置" prop="location">
            <el-input v-model="deviceForm.location" placeholder="输入设备位置" />
          </el-form-item>

          <el-form-item label="视频流地址" prop="ip_address">
            <el-input v-model="deviceForm.ip_address" placeholder="0=本机摄像头，或 rtsp://、http:// 视频流地址" />
          </el-form-item>
          <el-form-item label="Edge 主机" prop="edge_host">
            <el-input v-model="deviceForm.edge_host" placeholder="同机部署留空或填 127.0.0.1；跨机填 Edge 的 IP（如 192.168.1.100）" />
          </el-form-item>
        </el-form>

        <template #footer>
          <el-button @click="showCreateDialog = false">取消</el-button>
          <el-button type="primary" :loading="deviceStore.loading" @click="handleDeviceSubmit">
            {{ editingDevice ? '更新' : '添加' }}
          </el-button>
        </template>
      </el-dialog>

      <!-- Video Stream Dialog -->
      <el-dialog
        v-model="showStreamDialog"
        title="视频流"
        width="90%"
        :before-close="closeStreamDialog"
      >
        <div v-if="streamingDevice" class="stream-container">
          <VideoPlayer
            v-if="streamStore.isStreaming(streamingDevice.id)"
            :device="streamingDevice"
            @close="closeStreamDialog"
          />
          <div v-else class="stream-loading">
            <LoadingSpinner text="连接视频流中..." />
          </div>
        </div>
      </el-dialog>

      <!-- Calibration Dialog -->
      <el-dialog
        v-model="showCalibrationDialog"
        title="设备校准"
        width="600px"
      >
        <CalibrationPanel
          v-if="calibratingDevice"
          :device="calibratingDevice"
          @close="showCalibrationDialog = false"
        />
      </el-dialog>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onUnmounted, onMounted, watch } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import {
  Plus,
  Refresh,
  More,
  Edit,
  Setting,
  VideoPlay,
  Delete,
  CircleCheck,
  Warning,
  Close
} from '@element-plus/icons-vue';
import type { FormInstance, FormRules } from 'element-plus';
import type { Device, CreateDeviceParams } from '@/types';
import AppLayout from '@/components/layout/AppLayout.vue';
import LoadingSpinner from '@/components/common/LoadingSpinner.vue';
import EmptyState from '@/components/common/EmptyState.vue';
import VideoPlayer from '@/components/video/VideoPlayer.vue';
import CalibrationPanel from '@/components/devices/CalibrationPanel.vue';
import { useDeviceStore, useStreamStore } from '@/store';

const deviceStore = useDeviceStore();
const streamStore = useStreamStore();

const showCreateDialog = ref(false);
const showStreamDialog = ref(false);
const showCalibrationDialog = ref(false);
const editingDevice = ref<Device | null>(null);
const streamingDevice = ref<Device | null>(null);
const calibratingDevice = ref<Device | null>(null);
const deviceFormRef = ref<FormInstance>();

const deviceForm = reactive<CreateDeviceParams>({
  name: '',
  location: '',
  ip_address: '',
  edge_host: ''
});

const deviceRules: FormRules = {
  name: [{ required: true, message: '请输入设备名称', trigger: 'blur' }],
  location: [{ required: true, message: '请输入设备位置', trigger: 'blur' }],
  ip_address: [
    { required: true, message: '请输入视频流地址', trigger: 'blur' },
    {
      validator: (_: unknown, v: string, cb: (e?: Error) => void) => {
        if (!v?.trim()) return cb(new Error('请输入视频流地址'));
        const val = v.trim();
        if (val === '0') return cb(); // 本机摄像头
        if (/^(rtsp|http|https):\/\/[^\s]+$/.test(val)) return cb();
        cb(new Error('请输入 0（本机摄像头）或 rtsp://、http://、https:// 开头的地址'));
      },
      trigger: 'blur'
    }
  ]
};

const getStatusIcon = (status: string | undefined) => {
  const s = (status || '').toLowerCase();
  const iconMap: Record<string, typeof CircleCheck> = {
    online: CircleCheck,
    offline: Close,
    maintenance: Warning
  };
  return iconMap[s] || Close;
};

const getStatusLabel = (status: string | undefined) => {
  const s = (status || '').toLowerCase();
  const labelMap: Record<string, string> = {
    online: '在线',
    offline: '离线',
    maintenance: '维护中'
  };
  return labelMap[s] || s || '未知';
};

const formatTime = (timestamp: string) => {
  return new Date(timestamp).toLocaleString('zh-CN');
};

const fetchDevices = async () => {
  await deviceStore.fetchDevices();
};

const handleDeviceAction = async (command: { action: string; device: Device }) => {
  const { action, device } = command;

  switch (action) {
    case 'edit':
      editingDevice.value = device;
      Object.assign(deviceForm, {
        name: device.name,
        location: device.location,
        ip_address: device.ip_address,
        edge_host: device.edge_host || ''
      });
      showCreateDialog.value = true;
      break;

    case 'calibrate':
      calibratingDevice.value = device;
      showCalibrationDialog.value = true;
      break;

    case 'stream':
      streamingDevice.value = device;
      showStreamDialog.value = true;
      await startVideoStream(device);
      break;

    case 'delete':
      await deleteDevice(device);
      break;
  }
};

const handleDeviceSubmit = async () => {
  if (!deviceFormRef.value) return;

  try {
    await deviceFormRef.value.validate();

    if (editingDevice.value) {
      const updated = await deviceStore.updateDevice(editingDevice.value.id, deviceForm);
      ElMessage.success('设备更新成功');
      showCreateDialog.value = false;
      resetDeviceForm();
      const prev = editingDevice.value;
      editingDevice.value = null;
      // 若设备在线且有视频源，自动启动视频流并显示
      if (updated?.status === 'online' && updated?.ip_address?.trim()) {
        streamingDevice.value = updated;
        showStreamDialog.value = true;
        await startVideoStream(updated);
      }
    } else {
      await deviceStore.createDevice(deviceForm);
      ElMessage.success('设备添加成功');
      showCreateDialog.value = false;
      resetDeviceForm();
      editingDevice.value = null;
    }
  } catch (error) {
    // Validation error
  }
};

const deleteDevice = async (device: Device) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除设备 "${device.name}" 吗？此操作不可恢复。`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    );

    await deviceStore.deleteDevice(device.id);
    ElMessage.success('设备删除成功');
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('设备删除失败');
    }
  }
};

const startVideoStream = async (device: Device) => {
  try {
    await streamStore.startStream(device.id);
  } catch (error: any) {
    const msg = error?.detail || error?.message || '启动视频流失败';
    ElMessage.error(msg);
    showStreamDialog.value = false;
  }
};

const closeStreamDialog = async () => {
  if (streamingDevice.value) {
    await streamStore.stopStream(streamingDevice.value.id);
  }
  showStreamDialog.value = false;
  streamingDevice.value = null;
};

const resetDeviceForm = () => {
  Object.assign(deviceForm, {
    name: '',
    location: '',
    ip_address: '',
    edge_host: ''
  });
};

/** 快速添加本机摄像头：预填表单并打开对话框 */
const openAddLocalCamera = () => {
  Object.assign(deviceForm, {
    name: '本机摄像头',
    location: '本地',
    ip_address: '0',
    edge_host: ''
  });
  editingDevice.value = null;
  showCreateDialog.value = true;
};

// Watch for dialog close to reset form
const stopWatchingCreateDialog = watch(showCreateDialog, (newValue) => {
  if (!newValue) {
    resetDeviceForm();
    editingDevice.value = null;
  }
});

onMounted(async () => {
  await fetchDevices();
});

onUnmounted(() => {
  stopWatchingCreateDialog();
});
</script>

<style scoped>
.devices-view {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.header-actions {
  justify-content: flex-start;
}

.devices-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.device-card {
  position: relative;
  min-height: 210px;
  padding: 16px;
  overflow: hidden;
  border-radius: 8px;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
}

.device-card:hover {
  border-color: rgba(28, 199, 255, 0.45);
  box-shadow: var(--shadow-glass), 0 0 26px rgba(28, 199, 255, 0.12);
  transform: translateY(-2px);
}

.device-card::after {
  position: absolute;
  top: 0;
  right: 0;
  width: 96px;
  height: 2px;
  content: '';
  background: currentColor;
  opacity: 0.58;
  box-shadow: 0 0 18px currentColor;
}

.device-card--online {
  color: var(--accent-emerald);
  border-color: rgba(57, 231, 159, 0.24);
}

.device-card--offline {
  color: var(--text-muted);
  border-color: rgba(126, 211, 255, 0.14);
}

.device-card--maintenance {
  color: var(--accent-amber);
  border-color: rgba(255, 186, 58, 0.26);
}

.device-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}

.device-status {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 9px;
  border: 1px solid currentColor;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.035);
  color: currentColor;
}

.status-icon {
  font-size: 16px;
}

.status-icon--online {
  color: var(--accent-emerald);
}

.status-icon--offline {
  color: var(--text-muted);
}

.status-icon--maintenance {
  color: var(--accent-amber);
}

.status-text {
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 780;
}

.device-content {
  display: grid;
  gap: 8px;
}

.device-name {
  margin: 0;
  color: #ffffff;
  font-size: 17px;
  font-weight: 850;
  line-height: 1.25;
}

.device-location {
  margin: 0;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 650;
}

.device-ip,
.device-edge-host {
  overflow: hidden;
  color: var(--text-muted);
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', monospace;
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.device-heartbeat {
  color: var(--text-muted);
  font-size: 12px;
}

.stream-tag {
  width: max-content;
  margin-top: 4px;
}

.loading-container,
.empty-container {
  padding: 24px;
  border-radius: 8px;
}

.stream-container {
  min-height: 400px;
}

.stream-loading {
  display: flex;
  height: 16rem;
  align-items: center;
  justify-content: center;
}

@media (max-width: 1180px) {
  .devices-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .devices-grid {
    grid-template-columns: 1fr;
  }
}
</style>

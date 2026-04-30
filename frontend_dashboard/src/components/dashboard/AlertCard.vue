<template>
  <div class="alert-card" :class="`alert-card--${alert.severity.toLowerCase()}`">
    <div class="alert-header">
      <div class="alert-type">
        <el-icon class="alert-icon">
          <component :is="getAlertIcon(alert.type)" />
        </el-icon>
        <span class="alert-type-text">{{ getAlertTypeLabel(alert.type) }}</span>
      </div>
      <div class="alert-severity">
        <el-tag :type="getSeverityType(alert.severity)" size="small">
          {{ getSeverityLabel(alert.severity) }}
        </el-tag>
      </div>
    </div>

    <div class="alert-content">
      <h4 class="alert-message">{{ alert.message }}</h4>

      <div class="alert-details">
        <div class="alert-device">
          <el-icon><Monitor /></el-icon>
          {{ alert.device_name || `设备 ${alert.device_id}` }}
        </div>

        <div class="alert-time">
          <el-icon><Clock /></el-icon>
          {{ formatTime(alert.timestamp) }}
        </div>
      </div>
    </div>

    <div v-if="alert.image_url" class="alert-image">
      <img :src="alert.image_url" :alt="alert.message" @click="showImageModal" />
    </div>

    <div class="alert-actions">
      <el-button
        v-if="!alert.is_acknowledged"
        type="primary"
        size="small"
        :loading="acknowledging"
        @click="acknowledge"
      >
        确认警报
      </el-button>

      <el-button
        v-if="alert.is_acknowledged"
        type="success"
        size="small"
        disabled
      >
        已确认
      </el-button>
    </div>

    <!-- Image Modal -->
    <el-dialog
      v-model="imageModalVisible"
      title="警报图片"
      width="80%"
      :before-close="closeImageModal"
    >
      <img v-if="alert.image_url" :src="alert.image_url" class="modal-image" :alt="alert.message" />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { ElMessage } from 'element-plus';
import {
  Lightning,
  Smoking,
  User,
  Location,
  Lock,
  Monitor,
  Clock
} from '@element-plus/icons-vue';
import type { Alert } from '@/types';
import { useAlertStore } from '@/store';

interface Props {
  alert: Alert;
}

const props = defineProps<Props>();

const alertStore = useAlertStore();
const acknowledging = ref(false);
const imageModalVisible = ref(false);

const getAlertIcon = (type: string) => {
  const iconMap = {
    fire_violation: Lightning,
    smoke_violation: Smoking,
    ppe_violation: User,
    distance_violation: Location,
    access_control: Lock
  };
  return iconMap[type as keyof typeof iconMap] || Monitor;
};

const getAlertTypeLabel = (type: string) => {
  const labelMap = {
    fire_violation: '火灾违规',
    smoke_violation: '烟雾违规',
    ppe_violation: 'PPE违规',
    distance_violation: '距离违规',
    access_control: '访问控制'
  };
  return labelMap[type as keyof typeof labelMap] || type;
};

const getSeverityLabel = (severity: string) => {
  const labelMap = {
    CRITICAL: '紧急',
    DANGER: '危险',
    WARNING: '警告'
  };
  return labelMap[severity as keyof typeof labelMap] || severity;
};

const getSeverityType = (severity: string) => {
  const typeMap = {
    CRITICAL: 'danger',
    DANGER: 'warning',
    WARNING: 'info'
  };
  return typeMap[severity as keyof typeof typeMap] || 'info';
};

const formatTime = (timestamp: string) => {
  return new Date(timestamp).toLocaleString('zh-CN');
};

const acknowledge = async () => {
  acknowledging.value = true;
  try {
    await alertStore.acknowledgeAlert(props.alert.id);
    ElMessage.success('警报已确认');
  } catch (error) {
    ElMessage.error('确认警报失败');
  } finally {
    acknowledging.value = false;
  }
};

const showImageModal = () => {
  imageModalVisible.value = true;
};

const closeImageModal = () => {
  imageModalVisible.value = false;
};
</script>

<style scoped>
.alert-card {
  padding: 14px;
  margin-bottom: 12px;
  border: 1px solid rgba(126, 211, 255, 0.18);
  border-radius: 8px;
  background:
    linear-gradient(145deg, rgba(255, 255, 255, 0.07), rgba(255, 255, 255, 0.018)),
    rgba(8, 29, 47, 0.72);
  box-shadow: var(--shadow-glass);
  backdrop-filter: blur(18px);
}

.alert-card--critical {
  border-color: rgba(255, 77, 104, 0.42);
  background-color: rgba(255, 77, 104, 0.08);
}

.alert-card--danger {
  border-color: rgba(255, 130, 58, 0.38);
  background-color: rgba(255, 130, 58, 0.08);
}

.alert-card--warning {
  border-color: rgba(255, 186, 58, 0.36);
  background-color: rgba(255, 186, 58, 0.08);
}

.alert-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.alert-type {
  display: flex;
  align-items: center;
}

.alert-icon {
  margin-right: 8px;
  color: #91e9ff;
  font-size: 18px;
}

.alert-type-text {
  color: #ffffff;
  font-weight: 800;
}

.alert-severity {
  font-size: 13px;
}

.alert-content {
  margin-bottom: 12px;
}

.alert-message {
  margin: 0 0 8px;
  color: var(--text-primary);
  font-weight: 750;
}

.alert-details {
  display: grid;
  gap: 4px;
  color: var(--text-secondary);
  font-size: 13px;
}

.alert-device,
.alert-time {
  display: flex;
  align-items: center;
}

.alert-device .el-icon,
.alert-time .el-icon {
  margin-right: 6px;
  color: #8ddfff;
}

.alert-image {
  margin-bottom: 12px;
}

.alert-image img {
  width: 100%;
  height: 128px;
  cursor: pointer;
  border: 1px solid rgba(126, 211, 255, 0.18);
  border-radius: 6px;
  object-fit: cover;
}

.alert-actions {
  display: flex;
  justify-content: flex-end;
}

.modal-image {
  width: 100%;
  max-height: 70vh;
  object-fit: contain;
}
</style>

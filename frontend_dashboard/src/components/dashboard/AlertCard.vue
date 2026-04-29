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
  @apply bg-white rounded-lg shadow-sm border p-4 mb-4;
}

.alert-card--critical {
  @apply border-red-300 bg-red-50;
}

.alert-card--danger {
  @apply border-orange-300 bg-orange-50;
}

.alert-card--warning {
  @apply border-yellow-300 bg-yellow-50;
}

.alert-header {
  @apply flex items-center justify-between mb-3;
}

.alert-type {
  @apply flex items-center;
}

.alert-icon {
  @apply mr-2 text-lg;
}

.alert-type-text {
  @apply font-medium text-gray-800;
}

.alert-severity {
  @apply text-sm;
}

.alert-content {
  @apply mb-3;
}

.alert-message {
  @apply text-gray-800 font-medium mb-2;
}

.alert-details {
  @apply text-sm text-gray-600 space-y-1;
}

.alert-device,
.alert-time {
  @apply flex items-center;
}

.alert-device .el-icon,
.alert-time .el-icon {
  @apply mr-1;
}

.alert-image {
  @apply mb-3;
}

.alert-image img {
  @apply w-full h-32 object-cover rounded cursor-pointer;
}

.alert-actions {
  @apply flex justify-end;
}

.modal-image {
  @apply w-full max-h-96 object-contain;
}
</style>
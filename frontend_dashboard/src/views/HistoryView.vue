<template>
  <AppLayout>
    <div class="history-view">
      <!-- Filters -->
      <div class="filters-section">
        <el-form :inline="true" :model="filters" class="filters-form">
          <el-form-item label="警报类型">
            <el-select
              v-model="filters.type"
              placeholder="选择类型"
              clearable
              class="filter-select"
            >
              <el-option
                v-for="type in alertTypes"
                :key="type.value"
                :label="type.label"
                :value="type.value"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="严重程度">
            <el-select
              v-model="filters.severity"
              placeholder="选择严重程度"
              clearable
              class="filter-select"
            >
              <el-option
                v-for="severity in severityOptions"
                :key="severity.value"
                :label="severity.label"
                :value="severity.value"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="设备">
            <el-select
              v-model="filters.device_id"
              placeholder="选择设备"
              clearable
              class="filter-select"
            >
              <el-option
                v-for="device in deviceStore.devices"
                :key="device.id"
                :label="`${device.name} (${device.location})`"
                :value="device.id"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="开始日期">
            <el-date-picker
              v-model="filters.start_date"
              type="datetime"
              placeholder="选择开始时间"
              format="YYYY-MM-DD HH:mm:ss"
              value-format="YYYY-MM-DD HH:mm:ss"
            />
          </el-form-item>

          <el-form-item label="结束日期">
            <el-date-picker
              v-model="filters.end_date"
              type="datetime"
              placeholder="选择结束时间"
              format="YYYY-MM-DD HH:mm:ss"
              value-format="YYYY-MM-DD HH:mm:ss"
            />
          </el-form-item>

          <el-form-item>
            <el-button type="primary" @click="fetchAlerts">
              <el-icon><Search /></el-icon>
              查询
            </el-button>
            <el-button @click="resetFilters">
              <el-icon><Refresh /></el-icon>
              重置
            </el-button>
          </el-form-item>
        </el-form>
      </div>

      <!-- Alerts Table -->
      <div class="table-section">
        <el-table
          :data="alertStore.historicalAlerts"
          :loading="alertStore.loading"
          stripe
          style="width: 100%"
        >
          <el-table-column prop="type" label="类型" width="120">
            <template #default="scope">
              <el-tag :type="getAlertTypeTag(scope.row.type)">
                {{ getAlertTypeLabel(scope.row.type) }}
              </el-tag>
            </template>
          </el-table-column>

          <el-table-column prop="severity" label="严重程度" width="100">
            <template #default="scope">
              <el-tag :type="getSeverityType(scope.row.severity)">
                {{ getSeverityLabel(scope.row.severity) }}
              </el-tag>
            </template>
          </el-table-column>

          <el-table-column prop="message" label="消息" min-width="200">
            <template #default="scope">
              <div class="message-cell">
                <span class="message-text">{{ scope.row.message }}</span>
                <img
                  v-if="scope.row.image_url"
                  :src="scope.row.image_url"
                  class="message-image"
                  @click="showImageModal(scope.row)"
                />
              </div>
            </template>
          </el-table-column>

          <el-table-column prop="device_name" label="设备" width="150">
            <template #default="scope">
              {{ scope.row.device_name || `设备 ${scope.row.device_id}` }}
            </template>
          </el-table-column>

          <el-table-column prop="timestamp" label="时间" width="180">
            <template #default="scope">
              {{ formatTime(scope.row.timestamp) }}
            </template>
          </el-table-column>

          <el-table-column prop="is_acknowledged" label="状态" width="100">
            <template #default="scope">
              <el-tag :type="scope.row.is_acknowledged ? 'success' : 'warning'">
                {{ scope.row.is_acknowledged ? '已确认' : '未确认' }}
              </el-tag>
            </template>
          </el-table-column>

          <el-table-column label="操作" width="120">
            <template #default="scope">
              <el-button
                v-if="!scope.row.is_acknowledged"
                type="primary"
                size="small"
                @click="acknowledgeAlert(scope.row)"
              >
                确认
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <!-- Pagination -->
        <div class="pagination-container">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :total="totalAlerts"
            :page-sizes="[10, 20, 50, 100]"
            layout="total, sizes, prev, pager, next, jumper"
            @size-change="handleSizeChange"
            @current-change="handleCurrentChange"
          />
        </div>
      </div>

      <!-- Image Modal -->
      <el-dialog
        v-model="imageModalVisible"
        title="警报图片"
        width="80%"
        :before-close="closeImageModal"
      >
        <img v-if="selectedAlert?.image_url" :src="selectedAlert.image_url" class="modal-image" :alt="selectedAlert.message" />
      </el-dialog>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import { ElMessage } from 'element-plus';
import { Search, Refresh } from '@element-plus/icons-vue';
import type { Alert } from '@/types';
import AppLayout from '@/components/layout/AppLayout.vue';
import { useAlertStore, useDeviceStore } from '@/store';

const alertStore = useAlertStore();
const deviceStore = useDeviceStore();

const currentPage = ref(1);
const pageSize = ref(20);
const totalAlerts = ref(0);
const imageModalVisible = ref(false);
const selectedAlert = ref<Alert | null>(null);

const filters = reactive({
  type: '',
  severity: '',
  device_id: null as number | null,
  start_date: '',
  end_date: ''
});

const alertTypes = [
  { label: '火灾违规', value: 'fire_violation' },
  { label: '烟雾违规', value: 'smoke_violation' },
  { label: 'PPE违规', value: 'ppe_violation' },
  { label: '距离违规', value: 'distance_violation' },
  { label: '访问控制', value: 'access_control' }
];

const severityOptions = [
  { label: '紧急', value: 'CRITICAL' },
  { label: '危险', value: 'DANGER' },
  { label: '警告', value: 'WARNING' }
];

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

const getAlertTypeTag = (type: string) => {
  const tagMap = {
    fire_violation: 'danger',
    smoke_violation: 'warning',
    ppe_violation: 'info',
    distance_violation: 'warning',
    access_control: 'info'
  };
  return tagMap[type as keyof typeof tagMap] || 'info';
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

const fetchAlerts = async () => {
  const params = {
    skip: (currentPage.value - 1) * pageSize.value,
    limit: pageSize.value,
    ...filters
  };

  await alertStore.fetchHistoricalAlerts(params);
  totalAlerts.value = alertStore.historicalAlerts.length;
};

const resetFilters = () => {
  Object.assign(filters, {
    type: '',
    severity: '',
    device_id: null,
    start_date: '',
    end_date: ''
  });
  currentPage.value = 1;
  fetchAlerts();
};

const handleSizeChange = (newSize: number) => {
  pageSize.value = newSize;
  currentPage.value = 1;
  fetchAlerts();
};

const handleCurrentChange = (newPage: number) => {
  currentPage.value = newPage;
  fetchAlerts();
};

const acknowledgeAlert = async (alert: Alert) => {
  try {
    await alertStore.acknowledgeAlert(alert.id);
    ElMessage.success('警报已确认');
    fetchAlerts(); // Refresh the list
  } catch (error) {
    ElMessage.error('确认警报失败');
  }
};

const showImageModal = (alert: Alert) => {
  selectedAlert.value = alert;
  imageModalVisible.value = true;
};

const closeImageModal = () => {
  imageModalVisible.value = false;
  selectedAlert.value = null;
};

onMounted(async () => {
  await deviceStore.fetchDevices();
  await fetchAlerts();
});
</script>

<style scoped>
.history-view {
  @apply space-y-6;
}

.filters-section {
  @apply bg-white rounded-lg shadow-sm p-6;
}

.filters-form {
  @apply space-y-4 md:space-y-0 md:space-x-4;
}

.filter-select {
  @apply w-40;
}

.table-section {
  @apply bg-white rounded-lg shadow-sm p-6;
}

.message-cell {
  @apply flex items-center space-x-2;
}

.message-text {
  @apply flex-1;
}

.message-image {
  @apply w-8 h-8 object-cover rounded cursor-pointer;
}

.pagination-container {
  @apply mt-6 flex justify-center;
}

.modal-image {
  @apply w-full max-h-96 object-contain;
}
</style>
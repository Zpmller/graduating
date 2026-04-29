<template>
  <div class="calibration-panel">
    <!-- YAML Configuration -->
    <div class="config-section">
      <h3 class="section-title">校准配置</h3>
      <div class="config-actions">
        <el-button
          type="primary"
          size="small"
          @click="loadConfig"
          :loading="loading"
        >
          加载配置
        </el-button>
        <el-button
          type="success"
          size="small"
          @click="saveConfig"
          :loading="loading"
        >
          保存配置
        </el-button>
      </div>
      <el-input
        v-model="yamlConfig"
        type="textarea"
        :rows="10"
        placeholder="YAML配置文件内容..."
        class="yaml-editor"
      />
    </div>

    <!-- Calibration Images -->
    <div class="images-section">
      <h3 class="section-title">校准图片</h3>
      <div class="image-upload">
        <el-upload
          ref="uploadRef"
          class="upload-demo"
          drag
          :action="Upload"
          :headers="uploadHeaders"
          multiple
          :limit="10"
          accept=".jpg,.jpeg,.png"
          :on-success="handleUploadSuccess"
          :on-error="handleUploadError"
          :before-upload="beforeUpload"
        >
          <el-icon class="el-icon--upload"><Upload /></el-icon>
          <div class="el-upload__text">
            将图片拖到此处，或 <em>点击上传</em>
          </div>
          <template #tip>
            <div class="el-upload__tip">
              只能上传jpg/png文件，且不超过10MB
            </div>
          </template>
        </el-upload>
      </div>
    </div>

    <!-- Error Display -->
    <ErrorMessage
      v-if="error"
      :message="error"
      @close="error = null"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { ElMessage } from 'element-plus';
import { Upload } from '@element-plus/icons-vue';
import type { Device } from '@/types';
import ErrorMessage from '@/components/common/ErrorMessage.vue';
import { useDeviceStore, useAuthStore } from '@/store';

interface Props {
  device: Device;
}

const props = defineProps<Props>();

defineEmits<{
  close: [];
}>();

const deviceStore = useDeviceStore();
const authStore = useAuthStore();

const yamlConfig = ref('');
const loading = ref(false);
const error = ref<string | null>(null);
const uploadRef = ref();

const uploadHeaders = computed(() => ({
  Authorization: `Bearer ${authStore.token}`
}));

const loadConfig = async () => {
  loading.value = true;
  error.value = null;

  try {
    yamlConfig.value = await deviceStore.getCalibrationConfig(props.device.id);
  } catch (err: any) {
    error.value = err.detail || '加载配置失败';
  } finally {
    loading.value = false;
  }
};

const saveConfig = async () => {
  if (!yamlConfig.value.trim()) {
    ElMessage.warning('请输入YAML配置内容');
    return;
  }

  loading.value = true;
  error.value = null;

  try {
    const blob = new Blob([yamlConfig.value], { type: 'text/yaml' });
    const file = new File([blob], 'calibration.yaml', { type: 'text/yaml' });

    await deviceStore.uploadCalibrationConfig(props.device.id, file);
    ElMessage.success('配置保存成功');
  } catch (err: any) {
    error.value = err.detail || '保存配置失败';
  } finally {
    loading.value = false;
  }
};

const handleUploadSuccess = (response: any, file: any, fileList: any[]) => {
  ElMessage.success('图片上传成功');
};

const handleUploadError = (err: any, file: any, fileList: any[]) => {
  ElMessage.error('图片上传失败');
};

const beforeUpload = (file: File) => {
  const isImage = file.type.startsWith('image/');
  const isLt10M = file.size / 1024 / 1024 < 10;

  if (!isImage) {
    ElMessage.error('只能上传图片文件!');
    return false;
  }
  if (!isLt10M) {
    ElMessage.error('上传图片大小不能超过 10MB!');
    return false;
  }
  return true;
};

onMounted(() => {
  loadConfig();
});
</script>

<style scoped>
.calibration-panel {
  @apply space-y-6;
}

.config-section,
.images-section {
  @apply bg-gray-50 rounded-lg p-4;
}

.section-title {
  @apply text-lg font-semibold mb-4;
}

.config-actions {
  @apply flex space-x-2 mb-4;
}

.yaml-editor {
  @apply font-mono;
}

.image-upload {
  @apply mt-4;
}

.upload-demo {
  @apply w-full;
}
</style>
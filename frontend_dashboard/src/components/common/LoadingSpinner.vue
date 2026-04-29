<template>
  <div class="loading-spinner" :class="{ 'loading-spinner--center': center }">
    <el-icon class="is-loading">
      <Loading />
    </el-icon>
    <span v-if="text" class="loading-text">{{ text }}</span>
  </div>
</template>

<script setup lang="ts">
import { Loading } from '@element-plus/icons-vue';

interface Props {
  text?: string;
  center?: boolean;
}

withDefaults(defineProps<Props>(), {
  center: false
});
</script>

<style scoped>
.loading-spinner {
  @apply flex items-center justify-center py-8;
}

.loading-spinner--center {
  @apply min-h-32;
}

.loading-text {
  @apply ml-2 text-gray-600;
}

.is-loading {
  @apply text-2xl text-blue-500;
}
</style>
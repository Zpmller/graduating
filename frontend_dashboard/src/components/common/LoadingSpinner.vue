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
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem 0;
}

.loading-spinner--center {
  min-height: 8rem;
}

.loading-text {
  margin-left: 8px;
  color: var(--text-secondary);
  font-weight: 650;
}

.is-loading {
  color: var(--accent-cyan);
  font-size: 24px;
  filter: drop-shadow(0 0 10px rgba(28, 199, 255, 0.45));
}
</style>

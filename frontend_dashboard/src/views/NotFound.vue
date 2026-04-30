<template>
  <div class="not-found">
    <ParticleBackdrop :quiet="true" />
    <el-result
      icon="error"
      title="404"
      sub-title="抱歉，您访问的页面不存在"
    >
      <template #extra>
        <router-link to="/">
          <el-button type="primary">返回首页</el-button>
        </router-link>
      </template>
    </el-result>
  </div>
</template>

<script setup lang="ts">
import ParticleBackdrop from '@/components/common/ParticleBackdrop.vue';
</script>

<style scoped>
.not-found {
  position: relative;
  display: flex;
  min-height: 100vh;
  align-items: center;
  justify-content: center;
}

.not-found :deep(.el-result) {
  position: relative;
  z-index: 1;
  padding: 32px;
  border: 1px solid rgba(126, 211, 255, 0.22);
  border-radius: 8px;
  background: rgba(8, 29, 47, 0.78);
  backdrop-filter: blur(18px);
}

.not-found :deep(.el-result__title p),
.not-found :deep(.el-result__subtitle p) {
  color: var(--text-primary);
}
</style>

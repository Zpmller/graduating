<template>
  <div class="not-found">
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
// NotFound.vue - 404 page component
</script>

<style scoped>
.not-found {
  @apply min-h-screen flex items-center justify-center;
}
</style>